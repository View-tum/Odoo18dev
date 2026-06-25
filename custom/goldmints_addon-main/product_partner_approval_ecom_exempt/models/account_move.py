from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class AccountMove(models.Model):
    _inherit = "account.move"

    @api.constrains('partner_id', 'move_type')
    def _check_partner_approved(self):
        for move in self:
            if move.is_invoice(include_receipts=True):
                # We must check the commercial_partner_id (Parent Company) because 
                # the invoice partner_id might be a child Invoice Address which is in draft state.
                partner = move.partner_id.commercial_partner_id if move.partner_id else False
                if partner and partner.approval_state != 'approved' and not partner.ecom_exempt:
                    raise ValidationError(_("Customer is not approved — Accounting Manager must approve before invoicing."))
