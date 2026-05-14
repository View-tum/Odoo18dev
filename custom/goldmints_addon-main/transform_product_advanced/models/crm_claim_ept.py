# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CrmClaimEpt(models.Model):
    _inherit = "crm.claim.ept"

    transform_id = fields.Many2one(
        "product.transform",
        string="Product Transform",
        readonly=True,
        copy=False,
    )

    @api.depends("picking_id", "claim_line_ids.transform_id.product_to_id")
    def _compute_move_product_ids(self):
        super()._compute_move_product_ids()
        for claim in self:
            products = claim.move_product_ids | claim.claim_line_ids.mapped("transform_id.product_to_id")
            claim.move_product_ids = [(6, 0, products.ids)]

    @api.depends("picking_id", "claim_line_ids.transform_id.lot_to_id")
    def _compute_lot_ids(self):
        super()._compute_lot_ids()
        for claim in self:
            lots = claim.claim_lot_ids | claim.claim_line_ids.mapped("transform_id.lot_to_id")
            claim.claim_lot_ids = [(6, 0, lots.ids)]

    def create_return_picking_lines(self, claim_lines, return_picking_wizard):
        return_lines = []
        lines = claim_lines or self.claim_line_ids
        for line in lines:
            move = self._get_source_move_for_claim_line(line, claim_lines=bool(claim_lines))
            if not move:
                raise UserError(
                    _(
                        "No source stock move found for RMA product %s. "
                        "If this is a transformed return, create or link the Product Transform before approving RMA."
                    )
                    % line.product_id.display_name
                )
            return_line_values = self.prepare_values_for_return_picking_line(
                line,
                return_picking_wizard,
                move,
            )
            return_line = self.env["stock.return.picking.line"].create(return_line_values)
            return_lines.append(return_line.id)
        return return_lines

    def _get_transform_for_claim_line(self, line):
        transform = line.transform_id
        if transform:
            return transform

        claim_transform = line.claim_id.transform_id
        if claim_transform and claim_transform.product_to_id == line.product_id:
            line.transform_id = claim_transform.id
            return claim_transform

        domain = [
            ("state", "=", "done"),
            ("product_to_id", "=", line.product_id.id),
        ]
        if line.claim_id.picking_id:
            domain.append(("picking_id", "=", line.claim_id.picking_id.id))
        if line.serial_lot_ids:
            compatible_lots = line.serial_lot_ids.filtered(
                lambda lot: lot.product_id == line.product_id
            )
            if compatible_lots:
                domain.append(("lot_to_id", "in", compatible_lots.ids))

        transform = self.env["product.transform"].search(domain, order="date desc, id desc", limit=1)
        if transform:
            line.transform_id = transform.id
        return transform

    def _get_source_move_for_claim_line(self, line, claim_lines=False):
        transform = self._get_transform_for_claim_line(line)
        if transform:
            return transform.original_move_id or line.move_id

        if line.move_id:
            return line.move_id

        picking = self.return_picking_id if claim_lines else self.picking_id
        if not picking:
            return self.env["stock.move"]

        domain = [
            ("product_id", "=", line.product_id.id),
            ("picking_id", "=", picking.id),
            ("state", "!=", "cancel"),
        ]
        if line.move_id.sale_line_id:
            domain.append(("sale_line_id", "=", line.move_id.sale_line_id.id))
        return self.env["stock.move"].search(domain, limit=1)

    def create_move_lines(self, new_picking_id):
        for claim_line in self.claim_line_ids:
            self._get_transform_for_claim_line(claim_line)
        if not self.claim_line_ids.filtered("transform_id"):
            return super().create_move_lines(new_picking_id)
        self.write({"return_picking_id": new_picking_id})
        for claim_line in self.claim_line_ids:
            if claim_line.transform_id:
                self._create_transform_return_move_lines(claim_line)
            else:
                self._create_standard_return_move_lines(claim_line)
        return self.return_picking_id

    def _get_move_line_qty(self, line):
        return line.quantity if "quantity" in line._fields else line.qty_done

    def _write_move_line_qty(self, line, quantity):
        field_name = "quantity" if "quantity" in line._fields else "qty_done"
        line.write({field_name: quantity})

    def _get_zero_return_move_lines(self, product):
        return self.return_picking_id.move_ids.mapped("move_line_ids").filtered(
            lambda line: line.product_id == product and self._get_move_line_qty(line) == 0.0
        )

    def _create_return_move_line(self, move, product, quantity, lot=False):
        StockMoveLine = self.env["stock.move.line"]
        quantity_field = "quantity" if "quantity" in StockMoveLine._fields else "qty_done"
        vals = {
            "move_id": move.id,
            "picking_id": self.return_picking_id.id,
            "product_id": product.id,
            "product_uom_id": product.uom_id.id,
            "location_id": move.location_id.id,
            "location_dest_id": move.location_dest_id.id,
            "company_id": move.company_id.id,
            quantity_field: quantity,
        }
        if lot:
            vals["lot_id"] = lot.id
        return StockMoveLine.create(vals)

    def _get_or_create_transform_lot(self, transform, source_lot=False):
        if not transform or transform.product_to_id.tracking == "none":
            return self.env["stock.lot"]
        if not transform.lot_to_id:
            transform._get_or_create_to_lot()
        if transform.lot_to_id and transform.lot_to_id.product_id == transform.product_to_id:
            return transform.lot_to_id
        source_lot = source_lot or transform.lot_from_id
        if not source_lot:
            return self.env["stock.lot"]
        lot = self.env["stock.lot"].search(
            [
                ("product_id", "=", transform.product_to_id.id),
                ("name", "=", source_lot.name),
                "|",
                ("company_id", "=", False),
                ("company_id", "=", transform.company_id.id),
            ],
            limit=1,
        )
        if not lot:
            lot = self.env["stock.lot"].create(
                {
                    "product_id": transform.product_to_id.id,
                    "name": source_lot.name,
                    "company_id": transform.company_id.id,
                }
            )
        transform.lot_to_id = lot.id
        return lot

    def _get_transform_return_lots(self, claim_line):
        product = claim_line.product_id
        compatible_lots = claim_line.serial_lot_ids.filtered(
            lambda lot: lot.product_id == product
        )
        if compatible_lots:
            return compatible_lots
        source_lot = claim_line.serial_lot_ids[:1] or claim_line.transform_id.lot_from_id
        lot = self._get_or_create_transform_lot(claim_line.transform_id, source_lot=source_lot)
        if lot:
            claim_line.serial_lot_ids = [(6, 0, lot.ids)]
        return lot

    def _create_transform_return_move_lines(self, claim_line):
        return_quantity = claim_line.quantity
        return_move = self.return_picking_id.move_ids.filtered(
            lambda move: move.product_id == claim_line.product_id and move.state != "cancel"
        )[:1]
        if not return_move:
            raise UserError(_("No return move found for transformed product %s.") % claim_line.product_id.display_name)

        lots = self._get_transform_return_lots(claim_line)
        if claim_line.product_id.tracking == "serial" and lots:
            remaining_qty = return_quantity
            for lot in lots:
                if remaining_qty <= 0:
                    break
                line_qty = min(1.0, remaining_qty)
                move_line = self._get_zero_return_move_lines(claim_line.product_id)[:1]
                if move_line:
                    move_line.write({"lot_id": lot.id})
                    self._write_move_line_qty(move_line, line_qty)
                else:
                    self._create_return_move_line(return_move, claim_line.product_id, line_qty, lot)
                remaining_qty -= line_qty
            return

        lot = lots[:1] if lots else self.env["stock.lot"]
        move_line = self._get_zero_return_move_lines(claim_line.product_id)[:1]
        if move_line:
            if lot:
                move_line.write({"lot_id": lot.id})
            self._write_move_line_qty(move_line, return_quantity)
        else:
            self._create_return_move_line(return_move, claim_line.product_id, return_quantity, lot)

    def _create_standard_return_move_lines(self, claim_line):
        return_quantity = claim_line.quantity
        if claim_line.serial_lot_ids:
            claim_line_by_lots = {}
            done_move_lines = claim_line.move_id.mapped("move_line_ids").filtered(
                lambda line: line.product_id == claim_line.product_id
            )
            for done_move in done_move_lines:
                move_line_lot = done_move.lot_id
                done_qty = self._get_move_line_qty(done_move)
                claim_line_by_lots[move_line_lot] = claim_line_by_lots.get(move_line_lot, 0.0) + done_qty

            processed_qty_by_lots = sum(
                claim_line_by_lots.get(serial_lot_id, 0.0)
                for serial_lot_id in claim_line.serial_lot_ids
            )
            if return_quantity > processed_qty_by_lots:
                raise UserError(
                    _("Please select proper Lots/Serial Numbers %s to process return for product %s.")
                    % (claim_line.serial_lot_ids.mapped("name"), claim_line.product_id.name)
                )

            update_number_lines = self._get_zero_return_move_lines(claim_line.product_id).filtered(
                lambda line: line.lot_id.id not in claim_line.serial_lot_ids.ids
            )
            return_move_lines = self._get_zero_return_move_lines(claim_line.product_id)
            return_move = self.return_picking_id.move_ids.filtered(
                lambda move: move.product_id == claim_line.product_id and move.state != "cancel"
            )[:1]

            for serial_lot_id in claim_line.serial_lot_ids:
                return_lot_move_lines = return_move_lines.filtered(lambda line: line.lot_id == serial_lot_id)
                if not return_lot_move_lines and update_number_lines:
                    return_move_line = update_number_lines[0]
                    return_move_line.write({"lot_id": serial_lot_id.id})
                    update_number_lines -= return_move_line
                elif return_lot_move_lines:
                    return_move_line = return_lot_move_lines[0]
                else:
                    return_move_line = self._create_return_move_line(
                        return_move,
                        claim_line.product_id,
                        0.0,
                        serial_lot_id,
                    )
                quantity = claim_line_by_lots.get(return_move_line.lot_id, 0.0)
                if quantity >= return_quantity:
                    self._write_move_line_qty(return_move_line, return_quantity)
                    break
                return_quantity -= quantity
                self._write_move_line_qty(return_move_line, quantity)
            return

        return_move_lines = self._get_zero_return_move_lines(claim_line.product_id)
        return_move_line = return_move_lines[:1]
        if return_move_line:
            self._write_move_line_qty(return_move_line, return_quantity)
            return
        return_move = self.return_picking_id.move_ids.filtered(
            lambda move: move.product_id == claim_line.product_id and move.state != "cancel"
        )[:1]
        if not return_move:
            raise UserError(_("No return move found for product %s.") % claim_line.product_id.display_name)
        self._create_return_move_line(return_move, claim_line.product_id, return_quantity)

    def check_and_create_refund_invoice(self, claim_lines):
        transform_lines = self.env["claim.line.ept"].browse(
            [line.id for line in claim_lines if line.transform_id]
        )
        standard_lines = self.env["claim.line.ept"].browse(
            [line.id for line in claim_lines if not line.transform_id]
        )
        if not transform_lines:
            return super().check_and_create_refund_invoice(claim_lines)

        refund_invoice_ids = {}
        if standard_lines:
            refund_invoice_ids = super().check_and_create_refund_invoice(standard_lines)
            if not refund_invoice_ids:
                return refund_invoice_ids

        for line in transform_lines:
            invoice_line = line.transform_id.invoice_line_id
            if not invoice_line:
                invoice_line = line.move_id.sale_line_id.invoice_lines.filtered(
                    lambda inv_line: inv_line.move_id.move_type == "out_invoice"
                    and inv_line.move_id.state != "cancel"
                )[:1]
            if not invoice_line:
                self.message_post(body=_("No invoice line found for transformed RMA line %s.") % line.product_id.display_name)
                return False
            if invoice_line.move_id.state != "posted":
                self.message_post(
                    body=_("The invoice was not posted. Please check invoice: <a href=# data-oe-model=account.move data-oe-id=%d>%s</a>")
                    % (invoice_line.move_id.id, invoice_line.move_id.display_name)
                )
                return False
            qty = line.quantity if self.is_rma_without_incoming else line.return_qty or line.quantity
            if qty <= 0:
                continue
            refund_line_vals = {
                line.product_id.id: qty,
                "price": line.transform_id._get_refund_price_unit_from_invoice_line(invoice_line),
                "tax_id": invoice_line.tax_ids.ids,
                "discount": invoice_line.discount,
                "sale_line_id": line.move_id.sale_line_id.id,
            }
            refund_invoice_ids.setdefault(invoice_line.move_id.id, []).append(refund_line_vals)
        return refund_invoice_ids


class CrmClaimLineEpt(models.Model):
    _inherit = "claim.line.ept"

    transform_id = fields.Many2one(
        "product.transform",
        string="Product Transform",
        readonly=True,
        copy=False,
    )
    transform_original_product_id = fields.Many2one(
        "product.product",
        string="Original Product",
        related="transform_id.product_from_id",
        readonly=True,
    )
    transform_invoice_id = fields.Many2one(
        "account.move",
        string="Original Invoice",
        related="transform_id.invoice_id",
        readonly=True,
    )

    def _compute_return_quantity(self):
        for record in self:
            record.return_qty = 0.0
            if not record.claim_id.return_picking_id:
                continue
            if record.transform_id:
                moves = record.claim_id.return_picking_id.move_ids.filtered(
                    lambda move: move.product_id == record.product_id
                    and move.origin_returned_move_id == record.move_id
                    and move.state != "cancel"
                )
                record.return_qty = sum(moves.mapped("quantity"))
                continue
            moves = record.claim_id.return_picking_id.move_ids.filtered(
                lambda move: move.sale_line_id.id == record.move_id.sale_line_id.id
                and move.product_id == record.product_id
                and move.origin_returned_move_id == record.move_id
                and move.state != "cancel"
            )
            record.return_qty = sum(moves.mapped("quantity"))

    def _compute_get_done_quantity(self):
        for record in self:
            if record.transform_id:
                record.done_qty = record.transform_id.qty_to
            else:
                record.done_qty = record.move_id.quantity

    @api.constrains("quantity", "transform_id")
    def check_qty(self):
        for line in self:
            if line.quantity < 0:
                raise UserError(_("Quantity must be positive number"))
            if line.transform_id:
                if line.quantity > line.transform_id.qty_to:
                    raise UserError(_("Quantity must be less than or equal to the transformed quantity"))
                continue
            if line.quantity > line.move_id.quantity:
                raise UserError(_("Quantity must be less than or equal to the delivered quantity"))
