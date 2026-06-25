from collections import defaultdict

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_is_zero


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
    factor = fields.Float(string="Pieces per Sold Unit", readonly=True)
    qty_return = fields.Float(string="Return Quantity", default=1.0)
    qty_source_equivalent = fields.Float(string="Equivalent Sold Quantity", readonly=True)
    returned_qty = fields.Float(string="Already Returned Quantity", readonly=True)
    max_return_qty = fields.Float(string="Maximum Return Quantity", readonly=True)
    return_lot_name = fields.Char(string="Returned Lot")
    return_lot_id = fields.Many2one("stock.lot", string="Returned Lot Record", readonly=True)
    customer_location_id = fields.Many2one("stock.location", string="Customer Location", readonly=True)
    destination_location_id = fields.Many2one(
        "stock.location",
        string="Return To",
        domain="[('usage', '=', 'internal')]",
    )
    rma_reason_id = fields.Many2one("rma.reason.ept", string="RMA Reason")
    refund_unit_price = fields.Float(string="Refund Unit Price (Excl. VAT)", compute="_compute_header_totals")
    refund_amount = fields.Monetary(string="Refund Amount (Excl. VAT)", compute="_compute_header_totals")
    stock_unit_cost = fields.Float(string="Return Stock Unit Cost", compute="_compute_header_totals")
    stock_value = fields.Monetary(string="Return Stock Value", compute="_compute_header_totals")
    currency_id = fields.Many2one(
        "res.currency",
        compute="_compute_currency_id",
        store=True,
        readonly=True,
    )
    auto_validate_return = fields.Boolean(default=False)
    auto_create_credit_note = fields.Boolean(default=False)
    auto_post_credit_note = fields.Boolean(default=False)
    line_ids = fields.One2many("rma.transform.return.line", "return_id", string="Return Lines", copy=True)
    line_count = fields.Integer(compute="_compute_document_counts")
    rma_claim_id = fields.Many2one("crm.claim.ept", readonly=True, copy=False)
    return_picking_id = fields.Many2one("stock.picking", readonly=True, copy=False)
    return_picking_ids = fields.Many2many(
        "stock.picking",
        "rma_transform_return_picking_rel",
        "return_id",
        "picking_id",
        string="Return Pickings",
        readonly=True,
        copy=False,
    )
    credit_note_id = fields.Many2one("account.move", readonly=True, copy=False)
    credit_note_ids = fields.Many2many(
        "account.move",
        "rma_transform_return_credit_note_rel",
        "return_id",
        "move_id",
        string="Credit Notes",
        readonly=True,
        copy=False,
    )
    source_picking_count = fields.Integer(compute="_compute_document_counts")
    return_picking_count = fields.Integer(compute="_compute_document_counts")
    credit_note_count = fields.Integer(compute="_compute_document_counts")
    svl_count = fields.Integer(string="Valuation Layers", compute="_compute_svl_count")
    note = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("transform_product_advanced.rma_transform_return") or "New"
        records = super().create(vals_list)
        for record in records:
            if record.source_picking_id and not record.line_ids:
                record.with_context(skip_rma_transform_header_sync=True).action_load_source()
            else:
                record._sync_header_from_lines()
        return records

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get("skip_rma_transform_header_sync"):
            source_fields = {"source_picking_id", "source_lot_id"}
            if source_fields.intersection(vals):
                for record in self.filtered(lambda item: item.state == "draft" and item.source_picking_id):
                    record.with_context(skip_rma_transform_header_sync=True).action_load_source()
            else:
                self._sync_header_from_lines()
        return res

    @api.depends("line_ids.invoice_id", "company_id")
    def _compute_currency_id(self):
        for record in self:
            record.currency_id = record.line_ids[:1].invoice_id.currency_id or record.company_id.currency_id

    @api.depends("line_ids", "line_ids.refund_amount", "line_ids.stock_value", "line_ids.refund_unit_price", "line_ids.stock_unit_cost")
    def _compute_header_totals(self):
        for record in self:
            lines = record.line_ids
            record.refund_amount = sum(lines.mapped("refund_amount"))
            record.stock_value = sum(lines.mapped("stock_value"))
            record.refund_unit_price = lines[:1].refund_unit_price
            record.stock_unit_cost = lines[:1].stock_unit_cost

    @api.depends("line_ids", "line_ids.source_picking_id", "return_picking_ids", "credit_note_ids")
    def _compute_document_counts(self):
        for record in self:
            source_pickings = record.line_ids.mapped("source_picking_id") or record.source_picking_id
            return_pickings = record.return_picking_ids or record.return_picking_id
            credit_notes = record.credit_note_ids or record.credit_note_id
            record.line_count = len(record.line_ids)
            record.source_picking_count = len(source_pickings)
            record.return_picking_count = len(return_pickings)
            record.credit_note_count = len(credit_notes)

    @api.depends("return_picking_ids.move_ids.stock_valuation_layer_ids", "return_picking_id.move_ids.stock_valuation_layer_ids")
    def _compute_svl_count(self):
        for record in self:
            moves = (record.return_picking_ids | record.return_picking_id).mapped("move_ids")
            record.svl_count = self.env["stock.valuation.layer"].search_count([("stock_move_id", "in", moves.ids)]) if moves else 0

    @api.onchange("source_picking_id", "source_lot_id")
    def _onchange_source(self):
        for record in self:
            if record.state == "draft" and record.source_picking_id:
                record._load_source_lines_from_header()

    def action_load_source(self):
        for record in self:
            if not record.source_picking_id:
                raise UserError(_("Please select an original delivery first."))
            record._load_source_lines_from_header()
        return True

    def _load_source_lines_from_header(self):
        self.ensure_one()
        Line = self.env["rma.transform.return.line"]
        line_vals = []
        for move, lot in Line._get_source_candidates(self.source_picking_id, self.source_lot_id):
            vals = Line._prepare_vals_from_source_move(move, source_lot=lot, return_record=self)
            line_vals.append((0, 0, vals))
        if not line_vals:
            self.line_ids = [(5, 0, 0)]
            self._clear_header_legacy_fields()
            raise UserError(_("No transformable delivery line was found for the selected original delivery."))
        self.line_ids = [(5, 0, 0)] + line_vals
        self._sync_header_from_lines()

    def _clear_header_legacy_fields(self):
        self.update(
            {
                "source_move_id": False,
                "sale_id": False,
                "sale_line_id": False,
                "invoice_id": False,
                "invoice_line_id": False,
                "rule_id": False,
                "product_from_id": False,
                "product_to_id": False,
                "partner_id": False,
                "customer_location_id": False,
                "destination_location_id": False,
                "return_lot_name": False,
                "return_lot_id": False,
                "factor": 0.0,
                "qty_return": 0.0,
                "qty_source_equivalent": 0.0,
                "returned_qty": 0.0,
                "max_return_qty": 0.0,
            }
        )

    def _sync_header_from_lines(self):
        for record in self:
            line = record.line_ids[:1]
            if not line:
                continue
            vals = {
                "partner_id": line.partner_id.id,
                "source_picking_id": line.source_picking_id.id,
                "source_move_id": line.source_move_id.id,
                "source_lot_id": line.source_lot_id.id,
                "sale_id": line.sale_id.id,
                "sale_line_id": line.sale_line_id.id,
                "invoice_id": line.invoice_id.id,
                "invoice_line_id": line.invoice_line_id.id,
                "rule_id": line.rule_id.id,
                "product_from_id": line.product_from_id.id,
                "product_to_id": line.product_to_id.id,
                "factor": line.factor,
                "qty_return": line.qty_return,
                "qty_source_equivalent": line.qty_source_equivalent,
                "returned_qty": line.returned_qty,
                "max_return_qty": line.max_return_qty,
                "return_lot_name": line.return_lot_name,
                "return_lot_id": line.return_lot_id.id,
                "customer_location_id": line.customer_location_id.id,
                "destination_location_id": line.destination_location_id.id,
            }
            record.with_context(skip_rma_transform_header_sync=True).write(vals)

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
                        "return_picking_ids": [(5, 0, 0)],
                        "credit_note_id": False,
                        "credit_note_ids": [(5, 0, 0)],
                    }
                )
                continue
            record.write({"state": "cancel"})
        return True

    def action_set_to_draft(self):
        for record in self:
            if record.state != "cancel":
                continue
            if record.rma_claim_id or record.return_picking_ids or record.return_picking_id or record.credit_note_ids or record.credit_note_id:
                raise UserError(_("Reset to draft is allowed only after generated RMA, return pickings and credit notes are cleared."))
            record.write({"state": "draft"})
        return True

    def _cancel_generated_documents(self):
        for record in self:
            record._check_cancel_generated_documents_allowed()
        for record in self:
            record._unlink_credit_notes()
            record._unlink_return_pickings()
            record._unlink_rma_claim()

    def _check_cancel_generated_documents_allowed(self):
        self.ensure_one()
        for credit_note in (self.credit_note_ids | self.credit_note_id).exists():
            if credit_note.state == "posted":
                raise UserError(_("Credit Note %s is posted. Reverse or cancel it before cancelling this RMA transform return.") % credit_note.display_name)
        for picking in (self.return_picking_ids | self.return_picking_id).exists():
            if picking.state == "done":
                raise UserError(_("Return Picking %s is done. Reverse the stock movement before cancelling this RMA transform return.") % picking.display_name)

    def _unlink_credit_notes(self):
        for credit_note in (self.credit_note_ids | self.credit_note_id).exists():
            if credit_note.state not in ("draft", "cancel"):
                raise UserError(_("Credit Note %s cannot be removed because it is in %s state.") % (credit_note.display_name, credit_note.state))
            credit_note.unlink()

    def _unlink_return_pickings(self):
        for picking in (self.return_picking_ids | self.return_picking_id).exists():
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
            record._ensure_lines_from_legacy_fields()
            record._validate_before_confirm()
            claim = record._create_rma_claim()
            credit_notes = record._create_credit_notes(claim) if record.auto_create_credit_note else self.env["account.move"]
            vals = {
                "state": "done",
                "rma_claim_id": claim.id,
                "credit_note_ids": [(6, 0, credit_notes.ids)],
                "credit_note_id": credit_notes[:1].id,
            }
            record.write(vals)
            claim_vals = {}
            if credit_notes:
                claim_vals["refund_invoice_ids"] = [(6, 0, credit_notes.ids)]
            if claim_vals:
                claim.write(claim_vals)
        return True

    def _ensure_lines_from_legacy_fields(self):
        Line = self.env["rma.transform.return.line"]
        for record in self.filtered(lambda item: not item.line_ids and item.source_move_id):
            vals = Line._prepare_vals_from_source_move(record.source_move_id, source_lot=record.source_lot_id, return_record=record)
            vals.update(
                {
                    "qty_return": record.qty_return or 1.0,
                    "return_lot_name": record.return_lot_name,
                    "destination_location_id": record.destination_location_id.id,
                    "rma_reason_id": record.rma_reason_id.id,
                }
            )
            record.write({"line_ids": [(0, 0, vals)]})

    def _validate_before_confirm(self):
        for record in self:
            if record.state != "draft":
                raise UserError(_("Only draft RMA transform returns can be confirmed."))
            if not record.line_ids:
                raise UserError(_("Please add at least one return line."))
            partners = record.line_ids.mapped("partner_id")
            companies = record.line_ids.mapped("company_id")
            currencies = record.line_ids.mapped("currency_id")
            if len(partners) > 1:
                raise UserError(_("All return lines must belong to the same customer."))
            if len(companies) > 1:
                raise UserError(_("All return lines must belong to the same company."))
            if len(currencies) > 1:
                raise UserError(_("All return lines must use the same currency."))
            record.line_ids._validate_before_confirm()
            record._validate_return_limits()

    def _validate_return_limits(self):
        for record in self:
            grouped = defaultdict(lambda: {"qty": 0.0, "line": self.env["rma.transform.return.line"]})
            for line in record.line_ids:
                key = (line.source_move_id.id, line.product_to_id.id)
                grouped[key]["qty"] += line.qty_return
                grouped[key]["line"] = line
            for values in grouped.values():
                line = values["line"]
                existing_qty = line._get_returned_qty(exclude_return=record)
                precision = line.product_to_id.uom_id.rounding
                if float_compare(values["qty"] + existing_qty, line.max_return_qty, precision_rounding=precision) > 0:
                    raise UserError(_("Return quantity exceeds the available transformed quantity from the original delivery."))

    def _create_rma_claim(self):
        self.ensure_one()
        first = self.line_ids[:1]
        claim = self.env["crm.claim.ept"].create(
            {
                "name": "%s - Transform Return" % self.name,
                "partner_id": first.partner_id.id,
                "partner_delivery_id": first.source_picking_id.partner_id.id,
                "picking_id": first.source_picking_id.id,
                "sale_id": first.sale_id.id,
                "invoice_id": first.invoice_id.id,
                "location_id": first.destination_location_id.id,
                "company_id": self.company_id.id,
                "rma_transform_return_id": self.id,
            }
        )
        for line in self.line_ids:
            lot = line._get_or_create_return_lot()
            line_vals = {
                "claim_id": claim.id,
                "product_id": line.product_to_id.id,
                "quantity": line.qty_return,
                "move_id": line.source_move_id.id,
                "claim_type": "refund",
                "rma_transform_return_id": self.id,
                "rma_transform_return_line_id": line.id,
            }
            if line.rma_reason_id:
                line_vals["rma_reason_id"] = line.rma_reason_id.id
            if lot:
                line_vals["serial_lot_ids"] = [(6, 0, lot.ids)]
            claim_line = self.env["claim.line.ept"].create(line_vals)
            line.rma_claim_line_id = claim_line.id
        return claim

    def _create_return_pickings(self, claim):
        self.ensure_one()
        grouped = defaultdict(lambda: self.env["rma.transform.return.line"])
        for line in self.line_ids:
            picking_type = line.source_picking_id.picking_type_id.return_picking_type_id or line.source_picking_id.picking_type_id
            key = (picking_type.id, line.partner_id.id, line.customer_location_id.id, line.destination_location_id.id)
            grouped[key] |= line
        pickings = self.env["stock.picking"]
        for lines in grouped.values():
            picking = self._create_return_picking_for_lines(lines, claim)
            pickings |= picking
        if self.auto_validate_return and pickings:
            for picking in pickings:
                try:
                    picking.with_context(skip_sms=True)._action_done()
                except UserError as error:
                    if "check_ids" in picking._fields and hasattr(picking, "_check_for_quality_checks") and picking._check_for_quality_checks():
                        picking.message_post(body=_("Auto validation was skipped because quality checks are required: %s") % error)
                    else:
                        raise
        return pickings

    def _create_return_picking_for_lines(self, lines, claim):
        first = lines[:1]
        picking_type = first.source_picking_id.picking_type_id.return_picking_type_id or first.source_picking_id.picking_type_id
        Picking = self.env["stock.picking"]
        picking_vals = {
            "picking_type_id": picking_type.id,
            "partner_id": first.partner_id.id,
            "location_id": first.customer_location_id.id,
            "location_dest_id": first.destination_location_id.id,
            "company_id": self.company_id.id,
            "origin": self._build_return_origin(lines),
            "claim_id": claim.id,
        }
        if "return_id" in Picking._fields and len(lines.mapped("source_picking_id")) == 1:
            picking_vals["return_id"] = first.source_picking_id.id
        picking = Picking.create(picking_vals)
        for line in lines:
            move = line._create_return_stock_move(picking, claim)
            line.write(
                {
                    "return_picking_id": picking.id,
                    "return_move_id": move.id,
                }
            )
        return picking

    def _build_return_origin(self, lines):
        self.ensure_one()
        source_names = ", ".join(lines.mapped("source_picking_id.name"))
        invoice_names = ", ".join(lines.mapped("invoice_id.name"))
        return "%s / %s / %s" % (self.name, source_names, invoice_names)

    def _create_credit_notes(self, claim):
        self.ensure_one()
        grouped = defaultdict(lambda: self.env["rma.transform.return.line"])
        for line in self.line_ids:
            grouped[line.invoice_id] |= line
        credit_notes = self.env["account.move"]
        for invoice, lines in grouped.items():
            credit_note = self._create_credit_note_for_invoice(invoice, lines, claim)
            credit_notes |= credit_note
        if self.auto_post_credit_note and credit_notes:
            credit_notes.action_post()
        return credit_notes

    def _create_credit_note_for_invoice(self, invoice, lines, claim):
        line_commands = []
        for line in lines:
            line_commands.append((0, 0, line._prepare_credit_note_line_vals()))
        credit_note = self.env["account.move"].create(
            {
                "move_type": "out_refund",
                "partner_id": invoice.partner_id.id,
                "invoice_date": fields.Date.context_today(self),
                "journal_id": invoice.journal_id.id,
                "currency_id": invoice.currency_id.id,
                "company_id": self.company_id.id,
                "invoice_origin": ", ".join(lines.mapped("sale_id.name")),
                "ref": "%s / %s" % (self.name, invoice.name),
                "reversed_entry_id": invoice.id,
                "rma_transform_return_id": self.id,
                "rma_transform_claim_id": claim.id,
                "invoice_line_ids": line_commands,
            }
        )
        for line in lines:
            created_line = credit_note.invoice_line_ids.filtered(lambda item, line=line: item.rma_transform_return_line_id == line)[:1]
            line.write(
                {
                    "credit_note_id": credit_note.id,
                    "credit_note_line_id": created_line.id,
                }
            )
        return credit_note

    def action_view_source_picking(self):
        self.ensure_one()
        return self._action_view_records("stock.picking", self.line_ids.mapped("source_picking_id") or self.source_picking_id, _("Original Deliveries"))

    def action_view_return_picking(self):
        self.ensure_one()
        return self._action_view_records("stock.picking", self.return_picking_ids or self.return_picking_id, _("Return Pickings"))

    def action_view_credit_note(self):
        self.ensure_one()
        return self._action_view_records("account.move", self.credit_note_ids or self.credit_note_id, _("Credit Notes"))

    def action_view_rma_claim(self):
        self.ensure_one()
        return self._action_view_records("crm.claim.ept", self.rma_claim_id, _("RMA Claim"))

    def action_view_valuation_layers(self):
        self.ensure_one()
        moves = (self.return_picking_ids | self.return_picking_id).mapped("move_ids")
        if not moves:
            raise UserError(_("No return stock moves found for this RMA transform return."))
        domain = [("stock_move_id", "in", moves.ids)]
        layers = self.env["stock.valuation.layer"].search(domain)
        action = self.env["ir.actions.act_window"]._for_xml_id("stock_account.stock_valuation_layer_action")
        action["domain"] = domain
        action["context"] = {"search_default_group_by_product": 1}
        if len(layers) == 1:
            form_view = self.env.ref("stock_account.stock_valuation_layer_form")
            action["views"] = [(form_view.id, "form")]
            action["res_id"] = layers.id
        return action

    def _action_view_records(self, model, records, name):
        records = records.exists()
        if not records:
            return {"type": "ir.actions.act_window_close"}
        action = {
            "name": name,
            "type": "ir.actions.act_window",
            "res_model": model,
            "view_mode": "list,form",
            "domain": [("id", "in", records.ids)],
            "target": "current",
        }
        if len(records) == 1:
            action.update({"view_mode": "form", "res_id": records.id, "domain": []})
        return action


class RmaTransformReturnLine(models.Model):
    _name = "rma.transform.return.line"
    _description = "RMA Transform Return Line"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    return_id = fields.Many2one("rma.transform.return", required=True, ondelete="cascade", index=True)
    state = fields.Selection(related="return_id.state", store=True)
    company_id = fields.Many2one("res.company", related="return_id.company_id", store=True, readonly=True)
    currency_id = fields.Many2one("res.currency", compute="_compute_currency_id", store=True)
    source_picking_id = fields.Many2one(
        "stock.picking",
        string="Original Delivery",
        domain="[('state', '=', 'done'), ('picking_type_code', '=', 'outgoing')]",
    )
    source_move_id = fields.Many2one(
        "stock.move",
        string="Original Delivery Line",
        domain="[('picking_id', '=', source_picking_id), ('state', '=', 'done')]",
    )
    source_lot_id = fields.Many2one("stock.lot", string="Original Lot")
    partner_id = fields.Many2one("res.partner", readonly=True)
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
    qty_source_equivalent = fields.Float(string="Equivalent Sold Quantity", compute="_compute_quantities_and_costs", store=True)
    returned_qty = fields.Float(string="Already Returned Quantity", compute="_compute_returned_qty")
    max_return_qty = fields.Float(string="Maximum Return Quantity", compute="_compute_returned_qty")
    return_lot_name = fields.Char(string="Returned Lot")
    return_lot_id = fields.Many2one("stock.lot", string="Returned Lot Record", readonly=True)
    customer_location_id = fields.Many2one("stock.location", string="Customer Location", readonly=True)
    destination_location_id = fields.Many2one(
        "stock.location",
        string="Return To",
        domain="[('usage', '=', 'internal')]",
    )
    rma_reason_id = fields.Many2one("rma.reason.ept", string="RMA Reason")
    refund_unit_price = fields.Float(string="Refund Unit Price (Excl. VAT)", compute="_compute_refund_amounts")
    refund_amount = fields.Monetary(string="Refund Amount (Excl. VAT)", compute="_compute_refund_amounts")
    stock_unit_cost = fields.Float(string="Return Stock Unit Cost", compute="_compute_quantities_and_costs", store=True)
    stock_value = fields.Monetary(string="Return Stock Value", compute="_compute_quantities_and_costs", store=True)
    rma_claim_line_id = fields.Many2one("claim.line.ept", readonly=True, copy=False)
    return_picking_id = fields.Many2one("stock.picking", readonly=True, copy=False)
    return_move_id = fields.Many2one("stock.move", readonly=True, copy=False)
    credit_note_id = fields.Many2one("account.move", readonly=True, copy=False)
    credit_note_line_id = fields.Many2one("account.move.line", readonly=True, copy=False)
    note = fields.Char()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_loaded_source_fields_after_save()
        if not self.env.context.get("skip_rma_transform_header_sync"):
            records.mapped("return_id")._sync_header_from_lines()
        return records

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get("skip_rma_transform_line_source_sync") and {"source_picking_id", "source_lot_id", "source_move_id"}.intersection(vals):
            self._sync_loaded_source_fields_after_save()
        if not self.env.context.get("skip_rma_transform_header_sync"):
            self.mapped("return_id")._sync_header_from_lines()
        return res

    def unlink(self):
        returns = self.mapped("return_id")
        res = super().unlink()
        if not self.env.context.get("skip_rma_transform_header_sync"):
            returns._sync_header_from_lines()
        return res

    @api.depends("invoice_id", "return_id.company_id")
    def _compute_currency_id(self):
        for line in self:
            line.currency_id = line.invoice_id.currency_id or line.return_id.company_id.currency_id

    @api.depends("source_move_id", "rule_id", "rule_id.qty_to", "rule_id.reverse", "qty_return")
    def _compute_quantities_and_costs(self):
        for line in self:
            factor = line._get_factor()
            line.factor = factor
            line.qty_source_equivalent = line.qty_return / factor if factor else 0.0
            line.stock_unit_cost = line._get_stock_unit_cost()
            line.stock_value = line.stock_unit_cost * line.qty_return

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
        for line in self:
            line.refund_unit_price = line._get_refund_unit_price()
            line.refund_amount = line.refund_unit_price * line.qty_return

    @api.depends("source_move_id", "product_to_id")
    def _compute_returned_qty(self):
        for line in self:
            line.returned_qty = line._get_returned_qty()
            line.max_return_qty = line.source_move_id.quantity * line._get_factor() if line.source_move_id and line.product_to_id else 0.0

    @api.onchange("source_picking_id", "source_lot_id")
    def _onchange_source(self):
        for line in self:
            if line.state != "draft":
                continue
            line._load_source_from_inputs()

    @api.onchange("source_move_id")
    def _onchange_source_move_id(self):
        for line in self:
            if line.source_move_id:
                line._apply_source_move(line.source_move_id)

    @api.onchange("rule_id")
    def _onchange_rule_id(self):
        for line in self:
            if line.rule_id:
                line.product_to_id = line.rule_id.product_to_id
                line.factor = line._get_factor()
                line.return_lot_name = line.return_lot_name or line.source_lot_id.name

    @api.model
    def _get_source_candidates(self, picking, source_lot=False):
        result = []
        if not picking:
            return result
        source_products = self._get_transform_source_products()
        moves = picking.move_ids.filtered(lambda move: move.state == "done" and move.sale_line_id and move.product_id in source_products)
        for move in moves:
            move_lines = move.move_line_ids.filtered(lambda item: item.product_id == move.product_id and self._get_move_line_qty(item) > 0)
            if source_lot:
                move_lines = move_lines.filtered(lambda item: item.lot_id == source_lot)
            lots = move_lines.mapped("lot_id")
            if lots:
                for lot in lots:
                    result.append((move, lot))
            elif not source_lot:
                result.append((move, self.env["stock.lot"]))
        return result

    @api.model
    def _get_move_line_qty(self, move_line):
        return getattr(move_line, "quantity", 0.0) or getattr(move_line, "qty_done", 0.0)

    @api.model
    def _prepare_vals_from_source_move(self, move, source_lot=False, return_record=False):
        invoice_line = self._get_invoice_line(move)
        rule = self._get_default_rule(move.product_id)
        lot = source_lot or move.move_line_ids.filtered("lot_id")[:1].lot_id
        destination = return_record.destination_location_id if return_record and return_record.destination_location_id else move.location_id
        vals = {
            "source_picking_id": move.picking_id.id,
            "source_move_id": move.id,
            "source_lot_id": lot.id,
            "partner_id": (move.picking_id.partner_id or move.sale_line_id.order_id.partner_id).id,
            "sale_id": move.sale_line_id.order_id.id,
            "sale_line_id": move.sale_line_id.id,
            "invoice_id": invoice_line.move_id.id,
            "invoice_line_id": invoice_line.id,
            "rule_id": rule.id,
            "product_from_id": move.product_id.id,
            "product_to_id": rule.product_to_id.id,
            "qty_return": 1.0,
            "return_lot_name": lot.name,
            "customer_location_id": move.location_dest_id.id,
            "destination_location_id": destination.id,
        }
        if return_record:
            vals.update(
                {
                    "return_id": return_record.id,
                    "rma_reason_id": return_record.rma_reason_id.id,
                }
            )
        return vals

    def _sync_loaded_source_fields_after_save(self):
        for line in self.filtered(lambda item: item.return_id.state == "draft" and (item.source_picking_id or item.source_move_id)):
            line._load_source_from_inputs()

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
        self.with_context(skip_rma_transform_line_source_sync=True).update(
            {
                "source_move_id": False,
                "sale_id": False,
                "sale_line_id": False,
                "invoice_id": False,
                "invoice_line_id": False,
                "rule_id": False,
                "product_from_id": False,
                "product_to_id": False,
                "partner_id": False,
                "customer_location_id": False,
                "return_lot_name": False,
            }
        )

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

    @api.model
    def _get_transform_source_products(self):
        return self.env["product.transform.rule"].search([("active", "=", True)]).mapped("product_from_id")

    def _apply_source_move(self, move):
        self.ensure_one()
        vals = self._prepare_vals_from_source_move(move, source_lot=self.source_lot_id, return_record=self.return_id)
        self.with_context(skip_rma_transform_line_source_sync=True).update(vals)

    @api.model
    def _get_invoice_line(self, move):
        invoice_lines = move.sale_line_id.invoice_lines.filtered(
            lambda line: line.move_id.move_type == "out_invoice" and line.move_id.state == "posted" and line.product_id == move.sale_line_id.product_id
        )
        if not invoice_lines:
            invoice_lines = move.sale_line_id.invoice_lines.filtered(
                lambda line: line.move_id.move_type == "out_invoice" and line.move_id.state != "cancel" and line.product_id == move.sale_line_id.product_id
            )
        return invoice_lines[:1]

    @api.model
    def _get_default_rule(self, product):
        rule = self.env["product.transform.rule"].search(
            [("product_from_id", "=", product.id), ("active", "=", True)],
            limit=1,
        )
        if not rule:
            raise UserError(_("No transform rule found for sold product %s.") % product.display_name)
        return rule

    def _get_factor(self, rule=False):
        self.ensure_one()
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
                raise UserError(_("Please configure a tax-excluded counterpart for tax %s before creating the credit note.") % tax.display_name)
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

    def _get_returned_qty(self, exclude_return=False):
        self.ensure_one()
        if not self.source_move_id or not self.product_to_id:
            return 0.0
        domain = [
            ("rma_transform_source_move_id", "=", self.source_move_id.id),
            ("product_id", "=", self.product_to_id.id),
            ("state", "!=", "cancel"),
        ]
        if exclude_return:
            domain.append(("rma_transform_return_id", "!=", exclude_return.id))
        moves = self.env["stock.move"].search(domain)
        return sum(moves.mapped("quantity"))

    def _validate_before_confirm(self):
        for line in self:
            if not line.source_move_id or not line.sale_id or not line.invoice_id or not line.invoice_line_id:
                line._load_source_from_inputs(raise_if_missing=True)
            if not line.invoice_line_id:
                raise UserError(_("No invoice line was found from the original delivery line."))
            if not line.rma_reason_id:
                raise UserError(_("Please select an RMA Reason for all return lines."))
            if not line.rule_id or not line.product_to_id:
                raise UserError(_("Please set a transform rule."))
            if line.product_to_id.tracking == "serial" and float_compare(line.qty_return, 1.0, precision_rounding=line.product_to_id.uom_id.rounding) != 0:
                raise UserError(_("Serial tracked returned products must be returned one by one."))
            if float_compare(line.qty_return, 0.0, precision_rounding=line.product_to_id.uom_id.rounding) <= 0:
                raise UserError(_("Return quantity must be positive."))
            if line.product_to_id.tracking != "none" and not line.return_lot_name:
                raise UserError(_("Please set the returned lot."))
            if not line.customer_location_id or line.customer_location_id.usage != "customer":
                raise UserError(_("The original delivery line must end at a customer location."))
            if not line.destination_location_id or line.destination_location_id.usage != "internal":
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
        if not lot:
            lot = self.env["stock.lot"].create(
                {
                    "name": self.return_lot_name,
                    "product_id": self.product_to_id.id,
                    "company_id": self.company_id.id,
                }
            )
        self.return_lot_id = lot.id
        return lot

    def _create_return_stock_move(self, picking, claim):
        self.ensure_one()
        lot = self._get_or_create_return_lot()
        StockMove = self.env["stock.move"]
        move_vals = {
            "name": "%s: %s" % (self.return_id.name, self.product_to_id.display_name),
            "product_id": self.product_to_id.id,
            "product_uom_qty": self.qty_return,
            "product_uom": self.product_to_id.uom_id.id,
            "picking_id": picking.id,
            "location_id": picking.location_id.id,
            "location_dest_id": picking.location_dest_id.id,
            "company_id": self.company_id.id,
            "sale_line_id": self.sale_line_id.id,
            "origin": self.return_id.name,
            "rma_transform_return_id": self.return_id.id,
            "rma_transform_return_line_id": self.id,
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
            "lot_id": lot.id if lot else False,
        }
        move_line = move.move_line_ids[:1]
        if move_line:
            move_line.write(line_vals)
            extra_lines = move.move_line_ids - move_line
            if extra_lines:
                extra_lines.unlink()
        else:
            line_vals["move_id"] = move.id
            self.env["stock.move.line"].create(line_vals)
        return move

    def _prepare_credit_note_line_vals(self):
        self.ensure_one()
        product_accounts = self.product_to_id.with_company(self.company_id)._get_product_accounts()
        product_income = self.product_to_id.with_company(self.company_id).property_account_income_id
        account = product_income or product_accounts.get("expense") or product_accounts.get("income") or self.invoice_line_id.account_id
        line_vals = {
            "product_id": self.product_to_id.id,
            "name": "%s / Return from %s / Original %s" % (self.product_to_id.display_name, self.source_picking_id.name, self.product_from_id.display_name),
            "quantity": self.qty_return,
            "product_uom_id": self.product_to_id.uom_id.id,
            "price_unit": self.refund_unit_price,
            "account_id": account.id,
            "tax_ids": [(6, 0, self._get_credit_note_tax_ids().ids)],
            "discount": 0.0,
            "rma_transform_return_id": self.return_id.id,
            "rma_transform_return_line_id": self.id,
            "rma_transform_source_invoice_line_id": self.invoice_line_id.id,
        }
        if "analytic_distribution" in self.env["account.move.line"]._fields:
            line_vals["analytic_distribution"] = self.invoice_line_id.analytic_distribution
        return line_vals


class StockMove(models.Model):
    _inherit = "stock.move"

    rma_transform_return_id = fields.Many2one("rma.transform.return", string="RMA Transform Return", copy=False)
    rma_transform_return_line_id = fields.Many2one("rma.transform.return.line", string="RMA Transform Return Line", copy=False)
    rma_transform_source_move_id = fields.Many2one("stock.move", string="RMA Transform Source Move", copy=False)
    rma_transform_rule_id = fields.Many2one("product.transform.rule", string="RMA Transform Rule", copy=False)
    rma_transform_claim_id = fields.Many2one("crm.claim.ept", string="RMA Transform Claim", copy=False)
    rma_transform_invoice_line_id = fields.Many2one("account.move.line", string="RMA Transform Invoice Line", copy=False)


class AccountMove(models.Model):
    _inherit = "account.move"

    rma_transform_return_id = fields.Many2one("rma.transform.return", string="RMA Transform Return", copy=False)
    rma_transform_claim_id = fields.Many2one("crm.claim.ept", string="RMA Transform Claim", copy=False)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    rma_transform_return_id = fields.Many2one("rma.transform.return", string="RMA Transform Return", copy=False)
    rma_transform_return_line_id = fields.Many2one("rma.transform.return.line", string="RMA Transform Return Line", copy=False)
    rma_transform_source_invoice_line_id = fields.Many2one("account.move.line", string="RMA Transform Source Invoice Line", copy=False)


class CrmClaimEpt(models.Model):
    _inherit = "crm.claim.ept"

    rma_transform_return_id = fields.Many2one("rma.transform.return", string="RMA Transform Return", readonly=True, copy=False)

    def approve_claim(self):
        if self.rma_transform_return_id:
            for line in self.claim_line_ids:
                self.check_claim_line_validate(line)
            self.write({"state": "approve"})
            if self.is_rma_without_incoming:
                self.write({"state": "process"})
            else:
                if not self.return_picking_id:
                    pickings = self.rma_transform_return_id._create_return_pickings(self)
                    if pickings:
                        vals = {
                            "return_picking_id": pickings[:1].id,
                        }
                        if "to_return_picking_ids" in self._fields:
                            vals["to_return_picking_ids"] = [(6, 0, pickings.ids)]
                        self.write(vals)
                        self.rma_transform_return_id.write({
                            "return_picking_id": pickings[:1].id,
                            "return_picking_ids": [(6, 0, pickings.ids)],
                        })
            self.sudo().action_rma_send_email()
            return True
        return super().approve_claim()

    def create_refund(self, claim_lines):
        if not self.rma_transform_return_id:
            return super().create_refund(claim_lines)
        transform = self.rma_transform_return_id
        credit_notes = transform._create_credit_notes(self)
        if credit_notes:
            self.write({"refund_invoice_ids": [(6, 0, credit_notes.ids)]})
        return bool(credit_notes)

    @api.depends("picking_id", "claim_line_ids.rma_transform_return_line_id.product_to_id", "claim_line_ids.rma_transform_return_id.product_to_id")
    def _compute_move_product_ids(self):
        super()._compute_move_product_ids()
        for claim in self:
            products = claim.move_product_ids | claim.claim_line_ids.mapped("rma_transform_return_line_id.product_to_id") | claim.claim_line_ids.mapped("rma_transform_return_id.product_to_id")
            claim.move_product_ids = [(6, 0, products.ids)]

    @api.depends("picking_id", "claim_line_ids.rma_transform_return_line_id.return_lot_id", "claim_line_ids.rma_transform_return_id.return_lot_id")
    def _compute_lot_ids(self):
        super()._compute_lot_ids()
        for claim in self:
            lots = claim.claim_lot_ids | claim.claim_line_ids.mapped("rma_transform_return_line_id.return_lot_id") | claim.claim_line_ids.mapped("rma_transform_return_id.return_lot_id")
            claim.claim_lot_ids = [(6, 0, lots.ids)]


class CrmClaimLineEpt(models.Model):
    _inherit = "claim.line.ept"

    rma_transform_return_id = fields.Many2one("rma.transform.return", string="RMA Transform Return", readonly=True, copy=False)
    rma_transform_return_line_id = fields.Many2one("rma.transform.return.line", string="RMA Transform Return Line", readonly=True, copy=False)
    rma_transform_original_product_id = fields.Many2one(
        "product.product",
        string="Original Product",
        compute="_compute_rma_transform_related",
        readonly=True,
    )
    rma_transform_invoice_id = fields.Many2one(
        "account.move",
        string="Original Invoice",
        compute="_compute_rma_transform_related",
        readonly=True,
    )

    @api.depends("rma_transform_return_line_id.product_from_id", "rma_transform_return_line_id.invoice_id", "rma_transform_return_id.product_from_id", "rma_transform_return_id.invoice_id")
    def _compute_rma_transform_related(self):
        for line in self:
            transform_line = line.rma_transform_return_line_id
            line.rma_transform_original_product_id = transform_line.product_from_id or line.rma_transform_return_id.product_from_id
            line.rma_transform_invoice_id = transform_line.invoice_id or line.rma_transform_return_id.invoice_id

    def _compute_return_quantity(self):
        super()._compute_return_quantity()
        for record in self.filtered(lambda item: item.rma_transform_return_line_id or item.rma_transform_return_id):
            transform_line = record.rma_transform_return_line_id
            if transform_line:
                moves = transform_line.return_move_id.filtered(lambda move: move.state != "cancel")
            else:
                moves = record.rma_transform_return_id.return_picking_id.move_ids.filtered(
                    lambda move: move.rma_transform_return_id == record.rma_transform_return_id and move.state != "cancel"
                )
            record.return_qty = sum(moves.mapped("quantity"))

    def _compute_get_done_quantity(self):
        super()._compute_get_done_quantity()
        for record in self.filtered(lambda item: item.rma_transform_return_line_id or item.rma_transform_return_id):
            transform_line = record.rma_transform_return_line_id
            record.done_qty = transform_line.max_return_qty if transform_line else record.rma_transform_return_id.max_return_qty

    @api.constrains("quantity", "transform_id", "rma_transform_return_id", "rma_transform_return_line_id")
    def check_qty(self):
        for line in self:
            if line.quantity < 0:
                raise UserError(_("Quantity must be positive number"))
            transform_line = line.rma_transform_return_line_id
            if transform_line:
                if float_compare(line.quantity, transform_line.max_return_qty, precision_rounding=line.product_id.uom_id.rounding) > 0:
                    raise UserError(_("Quantity must be less than or equal to the transformed return quantity"))
                continue
            if line.rma_transform_return_id:
                if float_compare(line.quantity, line.rma_transform_return_id.max_return_qty, precision_rounding=line.product_id.uom_id.rounding) > 0:
                    raise UserError(_("Quantity must be less than or equal to the transformed return quantity"))
                continue
            if line.transform_id:
                if line.quantity > line.transform_id.qty_to:
                    raise UserError(_("Quantity must be less than or equal to the transformed quantity"))
                continue
            if line.quantity > line.move_id.quantity:
                raise UserError(_("Quantity must be less than or equal to the delivered quantity"))
