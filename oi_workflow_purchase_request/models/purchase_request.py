from odoo import models, api, _
from odoo.addons.oi_workflow.api import *


class PurchaseRequest(models.Model):
    _name = "purchase.request"
    _inherit = ['approval.record', 'purchase.request']
    _default_field_readonly = "state != 'draft' and not user_can_approve"

    @api.model
    def _before_approval_states(self):
        return [('draft', _('PR'))]

    @api.model
    def _after_approval_states(self):
        return [('approved', _('Approved')), ('in_progress', _('In Progress')), ('done', _('Done')), ('rejected', _('Rejected')), ('cancel', _('Cancelled'))]

    def _approval_allowed(self):
        return self.user_can_approve

    @on_approve()
    def _on_approve_button_approve(self):
        return self.button_approved()
