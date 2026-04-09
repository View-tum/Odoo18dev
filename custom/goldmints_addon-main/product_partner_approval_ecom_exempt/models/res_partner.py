from odoo import api, fields, models, _
from odoo.exceptions import UserError

class ResPartner(models.Model):
    _inherit = "res.partner"

    approval_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("approved", "Approved"),
        ],
        default="draft",
        required=True,
        string="Approval State",
        tracking=True,
    )
    ecom_exempt = fields.Boolean(string="E‑Commerce Exempt")
    is_lock = fields.Boolean(string="is_lock")

    def action_approve(self):
        for record in self:
            if not self.env.user.has_group('account.group_account_manager'):
                raise UserError(_("Only Accounting Managers can approve products."))
            record.write({'approval_state': 'approved', 'is_lock': True})
            

    # @api.model_create_multi
    # def create(self, vals_list):
    #     # Detect creation from website/portal flows
    #     is_from_website = self.env.context.get('from_website') or self.env.context.get('website_id')
    #     is_portal_user = self.env.user.has_group('base.group_portal')
    #     for vals in vals_list:
    #         # Keep back-office partners in draft unless set explicitly
    #         if (is_from_website or is_portal_user) and not vals.get('approval_state'):
    #             vals['approval_state'] = 'approved'
    #             vals['ecom_exempt'] = True
    #     return super().create(vals_list)
