from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    billing_note_line_ids = fields.One2many(
        "vendor.billing.note.line", "purchase_line_id", string="Billing Note Lines"
    )
    qty_billing_noted = fields.Float(
        compute="_compute_qty_billing_noted", string="Billed in Notes"
    )

    @api.depends(
        "billing_note_line_ids.quantity", "billing_note_line_ids.billing_note_id.state"
    )
    def _compute_qty_billing_noted(self):
        for line in self:
            # คำนวณจำนวนที่ถูกนำไปวางบิลแล้ว (ไม่นับใบที่ถูกยกเลิก)
            valid_lines = line.billing_note_line_ids.filtered(
                lambda l: l.billing_note_id.state != "cancel"
            )
            line.qty_billing_noted = sum(valid_lines.mapped("quantity"))
