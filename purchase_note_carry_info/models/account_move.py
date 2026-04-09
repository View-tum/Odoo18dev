from odoo import api, fields, models

class AccountMove(models.Model):
    _inherit = "account.move"

    purchase_note = fields.Text(
        string="Purchase Note",
        compute="_compute_purchase_note",
        store=True,
        readonly=True,
        help="(365 custom) Note carried from the Purchase Order related to this vendor bill (readonly)."
    )

    @api.depends(
        "invoice_line_ids",
        "invoice_line_ids.purchase_line_id",
        "invoice_line_ids.purchase_line_id.order_id",
        "invoice_line_ids.purchase_line_id.order_id.purchase_note",
    )
    def _compute_purchase_note(self):
        for move in self:
            pos = move.invoice_line_ids.mapped("purchase_line_id.order_id")
            move.purchase_note = pos[:1].purchase_note if pos else False
