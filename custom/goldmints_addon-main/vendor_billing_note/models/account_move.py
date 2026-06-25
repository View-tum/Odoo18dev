from odoo import _, api, fields, models
from odoo.exceptions import UserError

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

    def action_create_vendor_billing_note(self):
        moves = self.filtered(lambda move: move.move_type in ('in_invoice', 'in_refund'))
        if not moves or len(moves) != len(self):
            raise UserError(_("Only vendor bills and vendor credit notes can be used to create a vendor billing note."))
        if moves.filtered(lambda move: move.state == 'cancel'):
            raise UserError(_("Cancelled vendor bills or credit notes cannot be used to create a vendor billing note."))
        if moves.filtered(lambda move: move.vendor_billing_note_id):
            raise UserError(_("Some selected vendor bills or credit notes already have a vendor billing note."))
        if len(moves.mapped('partner_id')) != 1:
            raise UserError(_("Please select documents from one vendor only."))
        if len(moves.mapped('currency_id')) > 1:
            raise UserError(_("Please select documents in one currency only."))
        if len(moves.mapped('company_id')) > 1:
            raise UserError(_("Please select documents from one company only."))

        billing_note = self.env['vendor.billing.note'].create({
            'partner_id': moves.partner_id.id,
            'company_id': moves.company_id.id,
            'selected_bill_ids': [(6, 0, moves.ids)],
        })

        return {
            'name': _('Vendor Billing Note'),
            'type': 'ir.actions.act_window',
            'res_model': 'vendor.billing.note',
            'view_mode': 'form',
            'res_id': billing_note.id,
            'target': 'current',
        }
    
    def unlink(self):
        bns_to_update = self.mapped('vendor_billing_note_id')
        res = super(AccountMove, self).unlink()
        if bns_to_update:
            bns_to_update._update_billed_state()
        return res
