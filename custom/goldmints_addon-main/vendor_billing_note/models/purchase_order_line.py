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

    def _is_fixed_asset_billing_note_line(self):
        self.ensure_one()
        category = self.product_id.categ_id
        return bool("is_fixed_asset" in category._fields and category.is_fixed_asset)

    def _get_billing_note_qty_basis(self):
        self.ensure_one()
        if self._is_fixed_asset_billing_note_line():
            return self.product_qty
        return self.qty_received

    def _get_qty_to_billing_note(self):
        self.ensure_one()
        return max(self._get_billing_note_qty_basis() - self.qty_billing_noted, 0.0)
