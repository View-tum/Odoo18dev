from odoo import models, api, _
from odoo.addons.oi_workflow.api import *

class SaleOrder(models.Model):
    _name = "sale.order"
    _inherit = ['approval.record', 'sale.order']
    _default_field_readonly = "state != 'draft' and not user_can_approve"
    
    @api.model
    def _before_approval_states(self):
        return [('draft', _('Quotation')),('sent', _('Quotation Sent'))]
    
    @api.model
    def _after_approval_states(self):
        return [('sale', _('Sales Order')), ('done', _('Locked')), ('rejected', _('Rejected')), ('cancel', _('Cancelled'))]    
       
    def _approval_allowed(self):
        return self.user_can_approve
    
    @on_approve()
    def _on_approve_button_approve(self):
        self.state = 'draft'
        return self.action_confirm()
        
    @on_approval()
    def _on_approval_validate_analytic(self):
        for order in self.with_context(validate_analytic = True):
            order.order_line._validate_analytic_distribution()