from odoo import api, fields, models

class AccountMove(models.Model):
    _inherit = "account.move"

    sale_note = fields.Text(
        string="Note",
        compute="_compute_note",
        store=True,
        readonly=False,
        help="(365 custom) Note carried over from the related Sales Order(s)."
    )

    @api.depends(
        "invoice_line_ids",
        "invoice_line_ids.sale_line_ids",
        "invoice_line_ids.sale_line_ids.order_id",
        "invoice_line_ids.sale_line_ids.order_id.sale_note",
    )
    def _compute_note(self):
        for move in self:
            sale_orders = move.invoice_line_ids.mapped("sale_line_ids.order_id")
            move.sale_note = sale_orders[:1].sale_note if sale_orders else False