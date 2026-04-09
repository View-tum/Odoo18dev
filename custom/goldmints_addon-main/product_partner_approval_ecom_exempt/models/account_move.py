from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class AccountMove(models.Model):
    _inherit = "account.move"

    @api.constrains('partner_id', 'move_type')
    def _check_partner_approved(self):
        for move in self:
            if move.is_invoice(include_receipts=True):
                partner = move.partner_id
                if partner and partner.approval_state != 'approved' and not partner.ecom_exempt:
                    raise ValidationError(_("Customer is not approved — Accounting Manager must approve before invoicing."))
