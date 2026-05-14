from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_is_zero, float_round


class RmaTransformReturn(models.Model):
    _name = "rma.transform.return"
    _description = "RMA Transform Return"
    _order = "date desc, id desc"

    name = fields.Char(default="New", readonly=True, copy=False)
    state = fields.Selection(
        [("draft", "Draft"), ("done", "Done"), ("cancel", "Cancelled")],
        default="draft",
        readonly=True,
        copy=False,
    )
    date = fields.Datetime(default=fields.Datetime.now, required=True)
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company, required=True)
    partner_id = fields.Many2one("res.partner", readonly=True)
    source_picking_id = fields.Many2one(
        "stock.picking",
        string="Original Delivery",
        domain="[('state', '=', 'done'), ('picking_type_code', '=', 'outgoing')]",
        required=True,
    )
    source_move_id = fields.Many2one(
        "stock.move",
        string="Original Delivery Line",
        domain="[('picking_id', '=', source_picking_id), ('state', '=', 'done')]",
    )
    source_lot_id = fields.Many2one("stock.lot", string="Original Lot")
    sale_id = fields.Many2one("sale.order", readonly=True)
    sale_line_id = fields.Many2one("sale.order.line", readonly=True)
    invoice_id = fields.Many2one("account.move", readonly=True)
    invoice_line_id = fields.Many2one("account.move.line", readonly=True)
    rule_id = fields.Many2one(
        "product.transform.rule",
        string="Transform Rule",
        domain="[('product_from_id', '=', product_from_id), ('active', '=', True)]",
    )
    product_from_id = fields.Many2one("product.product", string="Sold Product", readonly=True)
    product_to_id = fields.Many2one("product.product", string="Returned Product", readonly=True)
    factor = fields.Float(string="Pieces per Sold Unit", compute="_compute_quantities_and_costs", store=True)
    qty_return = fields.Float(string="Return Quantity", default=1.0, required=True)
    qty_source_equivalent = fields.Float(
        string="Equivalent Sold Quantity",
        compute="_compute_quantities_and_costs",
        store=True,
    )
    returned_qty = fields.Float(string="Already Returned Quantity", compute="_compute_returned_qty")
    max_return_qty = fields.Float(string="Maximum Return Quantity", compute="_compute_returned_qty")
    return_lot_name = fields.Char(string="Returned Lot")
    return_lot_id = fields.Many2one("stock.lot", string="Returned Lot Record", readonly=True)
    customer_location_id = fields.Many2one("stock.location", string="Customer Location", readonly=True)
    destination_location_id = fields.Many2one(
        "stock.location",
        string="Return To",
        domain="[('usage', '=', 'internal')]",
        required=True,
    )
    rma_reason_id = fields.Many2one("rma.reason.ept", string="RMA Reason")
    refund_unit_price = fields.Float(string="Refund Unit Price (Excl. VAT)", compute="_compute_refund_amounts")
    refund_amount = fields.Monetary(string="Refund Amount (Excl. VAT)", compute="_compute_refund_amounts")
    stock_unit_cost = fields.Float(string="Return Stock Unit Cost", compute="_compute_quantities_and_costs", store=True)
    stock_value = fields.Monetary(string="Return Stock Value", compute="_compute_quantities_and_costs", store=True)
    currency_id = fields.Many2one(
        "res.currency",
        compute="_compute_currency_id",
        store=True,
        readonly=True,
    )
    auto_validate_return = fields.Boolean(default=False)
    auto_create_credit_note = fields.Boolean(default=True)
    auto_post_credit_note = fields.Boolean(default=False)
    rma_claim_id = fields.Many2one("crm.claim.ept", readonly=True, copy=False)
    return_picking_id = fields.Many2one("stock.picking", readonly=True, copy=False)
    credit_note_id = fields.Many2one("account.move", readonly=True, copy=False)
    svl_count = fields.Integer(string="Valuation Layers", compute="_compute_svl_count")
    note = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("transform_product_advanced.rma_transform_return") or "New"
        return super().create(vals_list)

    @api.depends("invoice_id", "company_id")
    def _compute_currency_id(self):
        for record in self:
            record.currency_id = record.invoice_id.currency_id or record.company_id.currency_id

    @api.depends("source_move_id", "rule_id", "rule_id.qty_to", "rule_id.reverse", "qty_return")
    def _compute_quantities_and_costs(self):
        for record in self:
            factor = record._get_factor()
            record.factor = factor
            record.qty_source_equivalent = record.qty_return / factor if factor else 0.0
            record.stock_unit_cost = record._get_stock_unit_cost()
            record.stock_value = record.stock_unit_cost * record.qty_return

    @api.depends(
        "invoice_line_id",
        "invoice_line_id.price_subtotal",
        "invoice_line_id.quantity",
        "invoice_line_id.product_uom_id.rounding",
        "rule_id",
        "rule_id.qty_to",
        "rule_id.reverse",
        "qty_return",
    )
    def _compute_refund_amounts(self):
        for record in self:
            record.refund_unit_price = record._get_refund_unit_price()
            record.refund_amount = record.refund_unit_price * record.qty_return

    @api.depends("source_move_id", "product_to_id")
    def _compute_returned_qty(self):
        StockMove = self.env["stock.move"]
        for record in self:
            record.returned_qty = 0.0
            record.max_return_qty = 0.0
            if not record.source_move_id or not record.product_to_id:
                continue
            moves = StockMove.search(
                [
                    ("rma_transform_source_move_id", "=", record.source_move_id.id),
                    ("product_id", "=", record.product_to_id.id),
                    ("state", "!=", "cancel"),
                ]
            )
            record.returned_qty = sum(moves.mapped("quantity"))
            record.max_return_qty = record.source_move_id.quantity * record._get_factor()

    @api.depends("return_picking_id.move_ids.stock_valuation_layer_ids")
    def _compute_svl_count(self):
        move_ids = self.mapped("return_picking_id.move_ids").ids
        count_by_move = {}
        if move_ids:
            rows = self.env["stock.valuation.layer"].read_group(
                [("stock_move_id", "in", move_ids)],
                ["stock_move_id"],
                ["stock_move_id"],
            )
            count_by_move = {
                row["stock_move_id"][0]: row["stock_move_id_count"]
                for row in rows
                if row.get("stock_move_id")
            }
        for record in self:
            record.svl_count = sum(
                count_by_move.get(move.id, 0)
                for move in record.return_picking_id.move_ids
            )

    @api.onchange("source_picking_id", "source_lot_id")
    def _onchange_source(self):
        for record in self:
            if record.state != "draft":
                continue
            record._load_source_from_inputs()

    @api.onchange("source_move_id")
    def _onchange_source_move_id(self):
        for record in self:
            if record.source_move_id:
                record._apply_source_move(record.source_move_id)

    @api.onchange("rule_id")
    def _onchange_rule_id(self):
        for record in self:
            if record.rule_id:
                record.product_to_id = record.rule_id.product_to_id
                record.factor = record._get_factor()
                record.return_lot_name = record.return_lot_name or record.source_lot_id.name

    def action_load_source(self):
        for record in self:
            record._load_source_from_inputs(raise_if_missing=True)
        return True

    def action_cancel(self):
        for record in self:
            if record.state == "cancel":
                continue
            if record.state == "done":
                record._cancel_generated_documents()
                record.write(
                    {
                        "state": "cancel",
                        "rma_claim_id": False,
                        "return_picking_id": False,
                        "credit_note_id": False,
                    }
                )
                continue
            record.write({"state": "cancel"})
        return True

    def action_set_to_draft(self):
        for record in self:
            if record.state != "cancel":
                continue
            if record.rma_claim_id or record.return_picking_id or record.credit_note_id:
                raise UserError(_("Reset to draft is allowed only after generated RMA, return picking and credit note are cleared."))
            record.write({"state": "draft"})
        return True

    def _cancel_generated_documents(self):
        for record in self:
            record._check_cancel_generated_documents_allowed()
        for record in self:
            record._unlink_credit_note()
            record._unlink_return_picking()
            record._unlink_rma_claim()

    def _check_cancel_generated_documents_allowed(self):
        self.ensure_one()
        credit_note = self.credit_note_id.exists()
        if credit_note and credit_note.state == "posted":
            raise UserError(
                _("Credit Note %s is posted. Reverse or cancel it before cancelling this RMA transform return.")
                % credit_note.display_name
            )
        picking = self.return_picking_id.exists()
        if picking and picking.state == "done":
            raise UserError(
                _("Return Picking %s is done. Reverse the stock movement before cancelling this RMA transform return.")
                % picking.display_name
            )

    def _unlink_credit_note(self):
        self.ensure_one()
        credit_note = self.credit_note_id.exists()
        if not credit_note:
            return
        if credit_note.state not in ("draft", "cancel"):
            raise UserError(
                _("Credit Note %s cannot be removed because it is in %s state.")
                % (credit_note.display_name, credit_note.state)
            )
        credit_note.unlink()

    def _unlink_return_picking(self):
        self.ensure_one()
        picking = self.return_picking_id.exists()
        if not picking:
            return
        if picking.state != "cancel":
            picking.action_cancel()
        picking.unlink()

    def _unlink_rma_claim(self):
        self.ensure_one()
        claim = self.rma_claim_id.exists()
        if not claim:
            return
        vals = {}
        if "return_picking_id" in claim._fields:
            vals["return_picking_id"] = False
        if "to_return_picking_ids" in claim._fields:
            vals["to_return_picking_ids"] = [(5, 0, 0)]
        if "refund_invoice_ids" in claim._fields:
            vals["refund_invoice_ids"] = [(5, 0, 0)]
        if vals:
            claim.write(vals)
        claim.unlink()

    def action_confirm(self):
        for record in self:
            record._validate_before_confirm()
            claim = record._create_rma_claim()
            picking = record._create_return_picking(claim)
            credit_note = record._create_credit_note(claim) if record.auto_create_credit_note else self.env["account.move"]
            vals = {
                "state": "done",
                "rma_claim_id": claim.id,
                "return_picking_id": picking.id,
            }
            if credit_note:
                vals["credit_note_id"] = credit_note.id
            record.write(vals)
            claim_vals = {"return_picking_id": picking.id}
            if credit_note:
                claim_vals["refund_invoice_ids"] = [(4, credit_note.id)]
            claim.write(claim_vals)
        return True

    def action_view_source_picking(self):
        self.ensure_one()
        return self._action_view_record("stock.picking", self.source_picking_id.id, _("Original Delivery"))

    def action_view_return_picking(self):
        self.ensure_one()
        return self._action_view_record("stock.picking", self.return_picking_id.id, _("Return Picking"))

    def action_view_credit_note(self):
        self.ensure_one()
        return self._action_view_record("account.move", self.credit_note_id.id, _("Credit Note"))

    def action_view_rma_claim(self):
        self.ensure_one()
        return self._action_view_record("crm.claim.ept", self.rma_claim_id.id, _("RMA Claim"))

    def action_view_valuation_layers(self):
        self.ensure_one()
        moves = self.return_picking_id.move_ids
        if not moves:
            raise UserError(_("No return stock moves found for this RMA transform return."))
        domain = [("stock_move_id", "in", moves.ids)]
        layers = self.env["stock.valuation.layer"].search(domain)
        action = self.env["ir.actions.act_window"]._for_xml_id("stock_account.stock_valuation_layer_action")
        action["domain"] = domain
        action["context"] = {
            "search_default_group_by_product": 1,
        }
        if len(layers) == 1:
            form_view = self.env.ref("stock_account.stock_valuation_layer_form")
            action["views"] = [(form_view.id, "form")]
            action["res_id"] = layers.id
        return action

    def _action_view_record(self, model, res_id, name):
        return {
            "name": name,
            "type": "ir.actions.act_window",
            "res_model": model,
            "view_mode": "form",
            "res_id": res_id,
            "target": "current",
        }

    def _load_source_from_inputs(self, raise_if_missing=False):
        self.ensure_one()
        move = self.source_move_id if self._source_move_matches_inputs(self.source_move_id) else self.env["stock.move"]
        if not move:
            move = self._find_source_move()
        if not move:
            self._clear_loaded_source_fields()
            if raise_if_missing:
                raise UserError(_("No done delivery line was found for the selected lot and delivery."))
            return
        self._apply_source_move(move)

    def _source_move_matches_inputs(self, move):
        self.ensure_one()
        if not move or move.state != "done" or not move.sale_line_id:
            return False
        if self.source_picking_id and move.picking_id != self.source_picking_id:
            return False
        if self.source_lot_id and self.source_lot_id not in move.move_line_ids.mapped("lot_id"):
            return False
        source_products = self._get_transform_source_products()
        if source_products and move.product_id not in source_products:
            return False
        return True

    def _clear_loaded_source_fields(self):
        self.ensure_one()
        self.source_move_id = False
        self.sale_id = False
        self.sale_line_id = False
        self.invoice_id = False
        self.invoice_line_id = False
        self.rule_id = False
        self.product_from_id = False
        self.product_to_id = False
        self.partner_id = False
        self.customer_location_id = False
        self.return_lot_name = False

    def _find_source_move(self):
        self.ensure_one()
        MoveLine = self.env["stock.move.line"]
        source_products = self._get_transform_source_products()
        domain = [
            ("state", "=", "done"),
            ("picking_id.picking_type_code", "=", "outgoing"),
            ("move_id.sale_line_id", "!=", False),
        ]
        if source_products:
            domain.append(("product_id", "in", source_products.ids))
        if self.source_picking_id:
            domain.append(("picking_id", "=", self.source_picking_id.id))
        if self.source_lot_id:
            domain.append(("lot_id", "=", self.source_lot_id.id))
        lines = MoveLine.search(domain, order="date desc, id desc", limit=1)
        if lines:
            return lines.move_id
        if self.source_picking_id:
            moves = self.source_picking_id.move_ids.filtered(lambda move: move.state == "done" and move.sale_line_id)
            if source_products:
                moves = moves.filtered(lambda move: move.product_id in source_products)
            return moves[:1]
        return self.env["stock.move"]

    def _get_transform_source_products(self):
        return self.env["product.transform.rule"].search([("active", "=", True)]).mapped("product_from_id")

    def _apply_source_move(self, move):
        self.ensure_one()
        invoice_line = self._get_invoice_line(move)
        rule = self.rule_id
        if not rule or rule.product_from_id != move.product_id:
            rule = self._get_default_rule(move.product_id)
        lot = self.source_lot_id or move.move_line_ids.filtered("lot_id")[:1].lot_id
        self.source_move_id = move
        self.source_picking_id = move.picking_id
        self.source_lot_id = lot
        self.sale_id = move.sale_line_id.order_id
        self.sale_line_id = move.sale_line_id
        self.partner_id = move.picking_id.partner_id or move.sale_line_id.order_id.partner_id
        self.invoice_line_id = invoice_line
        self.invoice_id = invoice_line.move_id
        self.product_from_id = move.product_id
        self.rule_id = rule
        self.product_to_id = rule.product_to_id
        self.factor = self._get_factor(rule)
        self.customer_location_id = move.location_dest_id
        self.destination_location_id = move.location_id
        self.return_lot_name = lot.name

    def _get_invoice_line(self, move):
        invoice_lines = move.sale_line_id.invoice_lines.filtered(
            lambda line: line.move_id.move_type == "out_invoice" and line.move_id.state == "posted"
        )
        if not invoice_lines:
            invoice_lines = move.sale_line_id.invoice_lines.filtered(
                lambda line: line.move_id.move_type == "out_invoice" and line.move_id.state != "cancel"
            )
        return invoice_lines[:1]

    def _get_default_rule(self, product):
        rule = self.env["product.transform.rule"].search(
            [("product_from_id", "=", product.id), ("active", "=", True)],
            limit=1,
        )
        if not rule:
            raise UserError(_("No transform rule found for sold product %s.") % product.display_name)
        return rule

    def _get_factor(self, rule=False):
        rule = rule or self.rule_id
        if not rule or float_is_zero(rule.qty_to, precision_rounding=0.000001):
            return 1.0
        return (1.0 / rule.qty_to) if rule.reverse else rule.qty_to

    def _get_refund_unit_price(self):
        self.ensure_one()
        if not self.invoice_line_id:
            return 0.0
        factor = self._get_factor()
        invoice_qty = self.invoice_line_id.quantity
        if float_is_zero(invoice_qty, precision_rounding=self.invoice_line_id.product_uom_id.rounding or 0.000001):
            return 0.0
        sold_unit_price = self.invoice_line_id.price_subtotal / invoice_qty
        return sold_unit_price / factor if factor else sold_unit_price

    def _get_credit_note_tax_ids(self):
        self.ensure_one()
        taxes = self.invoice_line_id.tax_ids
        if not taxes:
            return taxes
        mapped_taxes = self.env["account.tax"]
        Tax = self.env["account.tax"]
        for tax in taxes:
            if not tax.price_include:
                mapped_taxes |= tax
                continue
            domain = [
                ("company_id", "in", [False, tax.company_id.id]),
                ("amount", "=", tax.amount),
                ("amount_type", "=", tax.amount_type),
                ("type_tax_use", "=", tax.type_tax_use),
                ("price_include", "=", False),
                ("active", "=", True),
                ("id", "!=", tax.id),
            ]
            if tax.tax_group_id:
                domain.append(("tax_group_id", "=", tax.tax_group_id.id))
            replacement = Tax.search(domain, limit=1)
            if not replacement:
                raise UserError(
                    _("Please configure a tax-excluded counterpart for tax %s before creating the credit note.")
                    % tax.display_name
                )
            mapped_taxes |= replacement
        return mapped_taxes

    def _get_stock_unit_cost(self):
        self.ensure_one()
        if not self.source_move_id or not self.product_to_id:
            return 0.0
        layers = self.source_move_id.sudo().stock_valuation_layer_ids
        layer_qty = sum(abs(layer.quantity) for layer in layers if layer.quantity)
        layer_value = sum(abs(layer.value) for layer in layers)
        if layer_qty and layer_value:
            sold_unit_cost = layer_value / layer_qty
        else:
            sold_unit_cost = self.source_move_id.product_id.with_company(self.company_id).standard_price
        factor = self._get_factor()
        return sold_unit_cost / factor if factor else sold_unit_cost

    def _validate_before_confirm(self):
        self.ensure_one()
        if self.state != "draft":
            raise UserError(_("Only draft RMA transform returns can be confirmed."))
        if not self.source_move_id:
            self._load_source_from_inputs(raise_if_missing=True)
        if not self.invoice_line_id:
            raise UserError(_("No invoice line was found from the original delivery line."))
        if not self.rule_id or not self.product_to_id:
            raise UserError(_("Please set a transform rule."))
        if self.product_to_id.tracking == "serial" and float_compare(self.qty_return, 1.0, precision_rounding=self.product_to_id.uom_id.rounding) != 0:
            raise UserError(_("Serial tracked returned products must be returned one by one."))
        if float_compare(self.qty_return, 0.0, precision_rounding=self.product_to_id.uom_id.rounding) <= 0:
            raise UserError(_("Return quantity must be positive."))
        if float_compare(self.qty_return + self.returned_qty, self.max_return_qty, precision_rounding=self.product_to_id.uom_id.rounding) > 0:
            raise UserError(_("Return quantity exceeds the available transformed quantity from the original delivery."))
        if self.product_to_id.tracking != "none" and not self.return_lot_name:
            raise UserError(_("Please set the returned lot."))
        if not self.customer_location_id or self.customer_location_id.usage != "customer":
            raise UserError(_("The original delivery line must end at a customer location."))
        if not self.destination_location_id or self.destination_location_id.usage != "internal":
            raise UserError(_("Please set an internal return destination location."))

    def _get_or_create_return_lot(self):
        self.ensure_one()
        if self.product_to_id.tracking == "none":
            self.return_lot_id = False
            return self.env["stock.lot"]
        domain = [
            ("name", "=", self.return_lot_name),
            ("product_id", "=", self.product_to_id.id),
            "|",
            ("company_id", "=", False),
            ("company_id", "=", self.company_id.id),
        ]
        lot = self.env["stock.lot"].search(domain, limit=1)
        if lot:
            self.return_lot_id = lot
            return lot
        lot = self.env["stock.lot"].create(
            {
                "name": self.return_lot_name,
                "product_id": self.product_to_id.id,
                "company_id": self.company_id.id,
            }
        )
        self.return_lot_id = lot
        return lot

    def _create_rma_claim(self):
        self.ensure_one()
        lot = self._get_or_create_return_lot()
        line_vals = {
            "product_id": self.product_to_id.id,
            "quantity": self.qty_return,
            "move_id": self.source_move_id.id,
            "claim_type": "refund",
            "rma_transform_return_id": self.id,
        }
        if self.rma_reason_id:
            line_vals["rma_reason_id"] = self.rma_reason_id.id
        if lot:
            line_vals["serial_lot_ids"] = [(6, 0, lot.ids)]
        claim = self.env["crm.claim.ept"].create(
            {
                "name": "%s - %s" % (self.name, self.product_to_id.display_name),
                "partner_id": self.partner_id.id,
                "partner_delivery_id": self.source_picking_id.partner_id.id,
                "picking_id": self.source_picking_id.id,
                "sale_id": self.sale_id.id,
                "invoice_id": self.invoice_id.id,
                "location_id": self.destination_location_id.id,
                "company_id": self.company_id.id,
                "rma_transform_return_id": self.id,
                "claim_line_ids": [(0, 0, line_vals)],
            }
        )
        return claim

    def _create_return_picking(self, claim):
        self.ensure_one()
        lot = self._get_or_create_return_lot()
        picking_type = self.source_picking_id.picking_type_id.return_picking_type_id or self.source_picking_id.picking_type_id
        Picking = self.env["stock.picking"]
        picking_vals = {
            "picking_type_id": picking_type.id,
            "partner_id": self.partner_id.id,
            "location_id": self.customer_location_id.id,
            "location_dest_id": self.destination_location_id.id,
            "company_id": self.company_id.id,
            "origin": "%s / %s / %s" % (self.name, self.source_picking_id.name, self.invoice_id.name),
        }
        if "return_id" in Picking._fields:
            picking_vals["return_id"] = self.source_picking_id.id
        picking = Picking.create(picking_vals)
        StockMove = self.env["stock.move"]
        move_vals = {
            "name": "%s: %s" % (self.name, self.product_to_id.display_name),
            "product_id": self.product_to_id.id,
            "product_uom_qty": self.qty_return,
            "product_uom": self.product_to_id.uom_id.id,
            "picking_id": picking.id,
            "location_id": picking.location_id.id,
            "location_dest_id": picking.location_dest_id.id,
            "company_id": self.company_id.id,
            "sale_line_id": self.sale_line_id.id,
            "origin": self.name,
            "rma_transform_return_id": self.id,
            "rma_transform_source_move_id": self.source_move_id.id,
            "rma_transform_rule_id": self.rule_id.id,
            "rma_transform_claim_id": claim.id,
            "rma_transform_invoice_line_id": self.invoice_line_id.id,
        }
        if "price_unit" in StockMove._fields:
            move_vals["price_unit"] = self.stock_unit_cost
        if "to_refund" in StockMove._fields:
            move_vals["to_refund"] = True
        move = StockMove.create(move_vals)
        move._action_confirm()
        quantity_field = "quantity" if "quantity" in self.env["stock.move.line"]._fields else "qty_done"
        line_vals = {
            "picking_id": picking.id,
            "product_id": self.product_to_id.id,
            "product_uom_id": self.product_to_id.uom_id.id,
            "location_id": picking.location_id.id,
            "location_dest_id": picking.location_dest_id.id,
            "company_id": self.company_id.id,
            quantity_field: self.qty_return,
            "picked": True,
        }
        if lot:
            line_vals["lot_id"] = lot.id
        move_line = move.move_line_ids[:1]
        if move_line:
            move_line.write(line_vals)
            extra_lines = move.move_line_ids - move_line
            if extra_lines:
                extra_lines.unlink()
        else:
            line_vals["move_id"] = move.id
            self.env["stock.move.line"].create(line_vals)
        if self.auto_validate_return:
            picking.with_context(skip_sms=True)._action_done()
        return picking

    def _create_credit_note(self, claim):
        self.ensure_one()
        invoice = self.invoice_id
        invoice_line = self.invoice_line_id
        line_vals = {
            "product_id": self.product_to_id.id,
            "name": "%s / Return from %s / Original %s" % (self.product_to_id.display_name, self.source_picking_id.name, self.product_from_id.display_name),
            "quantity": self.qty_return,
            "product_uom_id": self.product_to_id.uom_id.id,
            "price_unit": self.refund_unit_price,
            "account_id": invoice_line.account_id.id,
            "tax_ids": [(6, 0, self._get_credit_note_tax_ids().ids)],
            "discount": 0.0,
            "rma_transform_return_id": self.id,
            "rma_transform_source_invoice_line_id": invoice_line.id,
        }
        if "analytic_distribution" in self.env["account.move.line"]._fields:
            line_vals["analytic_distribution"] = invoice_line.analytic_distribution
        move_vals = {
            "move_type": "out_refund",
            "partner_id": invoice.partner_id.id,
            "invoice_date": fields.Date.context_today(self),
            "journal_id": invoice.journal_id.id,
            "currency_id": invoice.currency_id.id,
            "company_id": self.company_id.id,
            "invoice_origin": self.sale_id.name,
            "ref": "%s / %s / %s" % (self.name, invoice.name, self.source_picking_id.name),
            "reversed_entry_id": invoice.id,
            "rma_transform_return_id": self.id,
            "invoice_line_ids": [(0, 0, line_vals)],
        }
        credit_note = self.env["account.move"].create(move_vals)
        if self.auto_post_credit_note:
            credit_note.action_post()
        return credit_note


class StockMove(models.Model):
    _inherit = "stock.move"

    rma_transform_return_id = fields.Many2one("rma.transform.return", string="RMA Transform Return", copy=False)
    rma_transform_source_move_id = fields.Many2one("stock.move", string="RMA Transform Source Move", copy=False)
    rma_transform_rule_id = fields.Many2one("product.transform.rule", string="RMA Transform Rule", copy=False)
    rma_transform_claim_id = fields.Many2one("crm.claim.ept", string="RMA Transform Claim", copy=False)
    rma_transform_invoice_line_id = fields.Many2one("account.move.line", string="RMA Transform Invoice Line", copy=False)


class AccountMove(models.Model):
    _inherit = "account.move"

    rma_transform_return_id = fields.Many2one("rma.transform.return", string="RMA Transform Return", copy=False)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    rma_transform_return_id = fields.Many2one("rma.transform.return", string="RMA Transform Return", copy=False)
    rma_transform_source_invoice_line_id = fields.Many2one("account.move.line", string="RMA Transform Source Invoice Line", copy=False)


class CrmClaimEpt(models.Model):
    _inherit = "crm.claim.ept"

    rma_transform_return_id = fields.Many2one("rma.transform.return", string="RMA Transform Return", readonly=True, copy=False)

    @api.depends("picking_id", "claim_line_ids.rma_transform_return_id.product_to_id")
    def _compute_move_product_ids(self):
        super()._compute_move_product_ids()
        for claim in self:
            products = claim.move_product_ids | claim.claim_line_ids.mapped("rma_transform_return_id.product_to_id")
            claim.move_product_ids = [(6, 0, products.ids)]

    @api.depends("picking_id", "claim_line_ids.rma_transform_return_id.return_lot_id")
    def _compute_lot_ids(self):
        super()._compute_lot_ids()
        for claim in self:
            lots = claim.claim_lot_ids | claim.claim_line_ids.mapped("rma_transform_return_id.return_lot_id")
            claim.claim_lot_ids = [(6, 0, lots.ids)]


class CrmClaimLineEpt(models.Model):
    _inherit = "claim.line.ept"

    rma_transform_return_id = fields.Many2one("rma.transform.return", string="RMA Transform Return", readonly=True, copy=False)
    rma_transform_original_product_id = fields.Many2one(
        "product.product",
        string="Original Product",
        related="rma_transform_return_id.product_from_id",
        readonly=True,
    )
    rma_transform_invoice_id = fields.Many2one(
        "account.move",
        string="Original Invoice",
        related="rma_transform_return_id.invoice_id",
        readonly=True,
    )

    def _compute_return_quantity(self):
        super()._compute_return_quantity()
        for record in self.filtered("rma_transform_return_id"):
            moves = record.rma_transform_return_id.return_picking_id.move_ids.filtered(
                lambda move: move.rma_transform_return_id == record.rma_transform_return_id and move.state != "cancel"
            )
            record.return_qty = sum(moves.mapped("quantity"))

    def _compute_get_done_quantity(self):
        super()._compute_get_done_quantity()
        for record in self.filtered("rma_transform_return_id"):
            record.done_qty = record.rma_transform_return_id.max_return_qty

    @api.constrains("quantity", "transform_id", "rma_transform_return_id")
    def check_qty(self):
        for line in self:
            if line.quantity < 0:
                raise UserError(_("Quantity must be positive number"))
            if line.rma_transform_return_id:
                if float_compare(
                    line.quantity,
                    line.rma_transform_return_id.max_return_qty,
                    precision_rounding=line.product_id.uom_id.rounding,
                ) > 0:
                    raise UserError(_("Quantity must be less than or equal to the transformed return quantity"))
                continue
            if line.transform_id:
                if line.quantity > line.transform_id.qty_to:
                    raise UserError(_("Quantity must be less than or equal to the transformed quantity"))
                continue
            if line.quantity > line.move_id.quantity:
                raise UserError(_("Quantity must be less than or equal to the delivered quantity"))
