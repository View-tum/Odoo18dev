from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PurchaseOrderStatusReportWizardLine(models.TransientModel):
    _inherit = "purchase.order.status.report.wizard.line"

    line_type = fields.Selection(
        [
            ("po", "PO / Service"),
            ("bill", "Bill / Credit Note"),
        ],
        string="Line Type",
        default="po",
    )
    account_move_id = fields.Many2one(
        "account.move",
        string="Vendor Bill/Credit Note",
        readonly=True,
    )
    move_type = fields.Selection(
        related="account_move_id.move_type",
        string="Document Type",
        readonly=True,
    )
    bill_invoice_date = fields.Date(
        related="account_move_id.invoice_date",
        string="Bill Date",
        readonly=True,
    )
    bill_ref = fields.Char(
        related="account_move_id.ref",
        string="Vendor Reference",
        readonly=True,
    )
    bill_payment_reference = fields.Char(
        related="account_move_id.payment_reference",
        string="Payment Reference",
        readonly=True,
    )
    bill_currency_id = fields.Many2one(
        "res.currency",
        string="Bill Currency",
        readonly=True,
    )
    bill_amount_untaxed = fields.Monetary(
        string="Bill Untaxed",
        currency_field="bill_currency_id",
        readonly=True,
    )
    bill_amount_total = fields.Monetary(
        string="Bill Total",
        currency_field="bill_currency_id",
        readonly=True,
    )
    bill_amount_residual = fields.Monetary(
        string="Open Balance",
        currency_field="bill_currency_id",
        readonly=True,
    )
    vendor_billing_note_id = fields.Many2one(
        related="account_move_id.vendor_billing_note_id",
        string="Billing Note",
        readonly=True,
    )


class PurchaseOrderStatusReport(models.AbstractModel):
    _inherit = "report.purchase_order_status_report.po_status_report"

    def _get_lines(self, wizard):
        lines = super()._get_lines(wizard)
        order_ids = [line["order_id"] for line in lines if line.get("is_header") and line.get("order_id")]
        if not order_ids:
            return lines

        moves = self.env["account.move"].search([
            ("move_type", "in", ("in_invoice", "in_refund")),
            ("state", "!=", "cancel"),
            ("invoice_line_ids.purchase_line_id.order_id", "in", order_ids),
        ])
        if wizard.product_id:
            moves = moves.filtered(
                lambda move: any(
                    line.product_id == wizard.product_id
                    for line in move.invoice_line_ids
                    if line.purchase_line_id
                )
            )

        moves_by_order = {}
        for move in moves:
            move_orders = move.invoice_line_ids.purchase_line_id.order_id.filtered(lambda order: order.id in order_ids)
            for order in move_orders:
                moves_by_order.setdefault(order.id, self.env["account.move"])
                moves_by_order[order.id] |= move

        result = []
        for line in lines:
            result.append(line)
            if not line.get("is_header"):
                continue
            bill_rows = moves_by_order.get(line["order_id"], self.env["account.move"])
            for move in bill_rows.sorted(key=lambda bill: (bill.invoice_date or bill.date or fields.Date.today(), bill.name or "", bill.id)):
                result.append(self._prepare_po_status_bill_line(line, move, wizard))
        return result

    def _prepare_po_status_bill_line(self, header_line, move, wizard):
        sign = -1.0 if move.move_type == "in_refund" else 1.0
        billing_note = move.vendor_billing_note_id
        move_lines = move.invoice_line_ids.filtered(lambda line: line.purchase_line_id.order_id.id == header_line["order_id"])
        if wizard.product_id:
            move_lines = move_lines.filtered(lambda line: line.product_id == wizard.product_id)
        products = move_lines.product_id.mapped("display_name")
        product_display = ", ".join(products[:2])
        if len(products) > 2:
            product_display = _("%s, ...") % product_display
        if not product_display:
            product_display = header_line.get("product_display") or ""

        billing_note_status = "no"
        if billing_note:
            billing_note_status = "draft" if billing_note.state == "draft" else "fully"

        return {
            **header_line,
            "line_type": "bill",
            "is_header": False,
            "po_line_id": move_lines[:1].purchase_line_id.id if move_lines else False,
            "account_move_id": move.id,
            "product": move_lines[:1].product_id if move_lines else False,
            "product_display": product_display,
            "receipt_ref": _("Vendor Bill") if move.move_type == "in_invoice" else _("Vendor Credit Note"),
            "receipt_date": move.invoice_date,
            "inv_ref": move.name,
            "qty": 0.0,
            "qty_received": 0.0,
            "qty_pending_invoice": 0.0,
            "uom": False,
            "unit_price": 0.0,
            "subtotal": sign * abs(move.amount_untaxed),
            "is_pending": False,
            "is_billable": not billing_note,
            "is_already_billed": bool(billing_note),
            "billing_note_status": billing_note_status,
            "bill_currency_id": move.currency_id.id,
            "bill_amount_untaxed": sign * abs(move.amount_untaxed),
            "bill_amount_total": sign * abs(move.amount_total),
            "bill_amount_residual": sign * abs(move.amount_residual),
        }


class PurchaseOrderStatusReportWizard(models.TransientModel):
    _inherit = "purchase.order.status.report.wizard"

    has_selected_lines = fields.Boolean(
        compute="_compute_has_selected_lines"
    )

    @api.depends("line_ids.is_selected")
    def _compute_has_selected_lines(self):
        for wizard in self:
            wizard.has_selected_lines = any(wizard.line_ids.mapped("is_selected"))

    def _prepare_preview_line_values(self, data):
        return {
            "order_id": data.get("order_id"),
            "po_line_id": data.get("po_line_id"),
            "picking_id": data.get("picking_id"),
            "service_acceptance_id": data.get("service_acceptance_id"),
            "source_document": data.get("source_document"),
            "receipt_ref": data.get("receipt_ref"),
            "inv_ref": data.get("inv_ref"),
            "date_order": data.get("order_date"),
            "expected_arrival": data.get("expected_arrival"),
            "vendor_id": data.get("vendor").id if data.get("vendor") else False,
            "product_id": data.get("product").id if data.get("product") else False,
            "product_display": data.get("product_display"),
            "qty": data.get("qty"),
            "qty_received": data.get("qty_received"),
            "qty_pending_invoice": data.get("qty_pending_invoice"),
            "uom_id": data.get("uom").id if data.get("uom") else False,
            "unit_price": data.get("unit_price"),
            "subtotal": data.get("subtotal"),
            "is_pending": data.get("is_pending", False),
            "is_header": data.get("is_header", False),
            "receipt_date": data.get("receipt_date"),
            "state": data.get("state"),
            "invoice_status": data.get("invoice_status"),
            "billing_note_status": data.get("billing_note_status"),
            "is_billable": data.get("is_billable", True),
            "is_already_billed": data.get("is_already_billed", False),
            "line_type": data.get("line_type", "po"),
            "account_move_id": data.get("account_move_id"),
            "bill_currency_id": data.get("bill_currency_id"),
            "bill_amount_untaxed": data.get("bill_amount_untaxed", 0.0),
            "bill_amount_total": data.get("bill_amount_total", 0.0),
            "bill_amount_residual": data.get("bill_amount_residual", 0.0),
        }

    def button_preview(self):
        self.ensure_one()
        self.line_ids = [(5, 0, 0)]
        lines_data = self.env["report.purchase_order_status_report.po_status_report"]._get_lines(self)
        self.line_ids = [(0, 0, self._prepare_preview_line_values(data)) for data in lines_data]
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
            "flags": {"mode": "edit"},
        }

    def action_select_all(self):
        action = super().action_select_all()
        action["flags"] = {"mode": "edit"}
        return action

    def action_select_bill_lines(self):
        self.ensure_one()
        self.line_ids.write({"is_selected": False})
        self.line_ids.filtered(lambda line: line.line_type == "bill" and line.is_billable).write({"is_selected": True})
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
            "flags": {"mode": "edit"},
        }

    def action_unselect_all(self):
        action = super().action_unselect_all()
        action["flags"] = {"mode": "edit"}
        return action

    def action_create_billing_note(self):
        self.ensure_one()
        selected_lines = self.line_ids.filtered(lambda line: line.is_selected and line.is_billable)
        if not selected_lines:
            raise ValidationError(_("Please select at least one billable line."))

        if len(selected_lines.mapped("vendor_id")) > 1:
            raise ValidationError(_("Please select lines from one vendor only."))

        selected_bill_lines = selected_lines.filtered("account_move_id")
        selected_po_lines = selected_lines - selected_bill_lines
        selected_moves = selected_bill_lines.mapped("account_move_id")
        billing_data = self._prepare_billing_note_data_from_po_status_lines(selected_po_lines)

        if selected_moves and not billing_data:
            return selected_moves.action_create_vendor_billing_note()
        if not billing_data and not selected_moves:
            raise ValidationError(_("The selected lines do not have any quantity or APD/CN available for a billing note."))

        action = self.env["purchase.order"].action_create_billing_note_from_data(
            selected_lines[0].vendor_id.id,
            billing_data,
        )
        if selected_moves:
            billing_note = self.env["vendor.billing.note"].browse(action["res_id"])
            billing_note.selected_bill_ids = [(6, 0, selected_moves.ids)]
        return action

    def _prepare_billing_note_data_from_po_status_lines(self, selected_lines):
        billing_data = []
        for order in selected_lines.mapped("order_id"):
            order_selected = selected_lines.filtered(lambda line: line.order_id == order)
            header_line = order_selected.filtered(lambda line: line.is_header)
            detail_lines = order_selected.filtered(lambda line: not line.is_header)

            if header_line:
                for po_line in order.order_line:
                    qty_to_bill = po_line._get_qty_to_billing_note()
                    if qty_to_bill > 0.001:
                        billing_data.append({
                            "purchase_line_id": po_line.id,
                            "quantity": qty_to_bill,
                        })
            elif detail_lines:
                for detail in detail_lines:
                    if detail.service_acceptance_id:
                        for sa_line in detail.service_acceptance_id.acceptance_line_ids:
                            if sa_line.qty_accepted > 0.001:
                                billing_data.append({
                                    "purchase_line_id": sa_line.po_line_id.id,
                                    "quantity": sa_line.qty_accepted,
                                    "picking_id": False,
                                    "service_acceptance_id": detail.service_acceptance_id.id,
                                })
                    elif detail.picking_id and detail.po_line_id:
                        billing_data.append({
                            "purchase_line_id": detail.po_line_id.id,
                            "quantity": detail.qty_received,
                            "picking_id": detail.picking_id.id,
                            "service_acceptance_id": False,
                        })
        return billing_data
