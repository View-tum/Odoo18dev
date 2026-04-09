
from odoo import models, api, _
from odoo.addons.oi_workflow.api import *

class PurchaseOrder(models.Model):
    _name = "purchase.order"
    _inherit = ['approval.record', 'purchase.order']
    _default_field_readonly = "state != 'draft' and not user_can_approve"
    
    @api.model
    def _before_approval_states(self):
        return [('draft', _('RFQ')),('sent', _('RFQ Sent'))]
    
    @api.model
    def _after_approval_states(self):
        return [('purchase', _('Purchase Order')), ('done', _('Locked')), ('rejected', _('Rejected')), ('cancel', _('Cancelled'))]    
       
    def _approval_allowed(self):
        return self.user_can_approve
    
    @on_approve()
    def _on_approve_button_approve(self):
        return self.button_approve()
        
    @on_approval()
    def _on_approval_validate_analytic(self):
        for order in self.with_context(validate_analytic = True):
            order.order_line._validate_analytic_distribution()        

