from odoo import api, fields, models

class AccountMove(models.Model):
    _inherit = 'account.move'

    vendor_billing_note_id = fields.Many2one(
        'vendor.billing.note',
        string='Billing Note Ref.',
        readonly=True,
        copy=False,
        help='อ้างอิงกลับไปยังใบวางบิลต้นทาง'
    )
    
    # 🌟 เมื่อมีการสร้าง Credit Note (หรือบิลใหม่) ให้อัปเดตยอดในใบวางบิลทันที
    @api.model_create_multi
    def create(self, vals_list):
        moves = super(AccountMove, self).create(vals_list)
        bns_to_update = moves.mapped('vendor_billing_note_id')
        if bns_to_update:
            bns_to_update._update_billed_state()
        return moves

    # 🌟 เมื่อกดปุ่ม Add Credit Note (Reverse) ให้ดึงเลขใบวางบิลติดไปด้วย
    def _reverse_move_vals(self, default_values, cancel=True):
        vals = super(AccountMove, self)._reverse_move_vals(default_values, cancel=cancel)
        if self.vendor_billing_note_id:
            vals['vendor_billing_note_id'] = self.vendor_billing_note_id.id
        return vals
    
    def button_cancel(self):
        res = super(AccountMove, self).button_cancel()
        for move in self:
            if move.vendor_billing_note_id:
                move.vendor_billing_note_id._update_billed_state()
        return res
    
    def unlink(self):
        bns_to_update = self.mapped('vendor_billing_note_id')
        res = super(AccountMove, self).unlink()
        if bns_to_update:
            bns_to_update._update_billed_state()
        return res