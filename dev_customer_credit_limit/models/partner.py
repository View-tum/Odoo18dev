# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle
#
##############################################################################

from odoo import models, fields

class res_partner(models.Model):
    _inherit= 'res.partner'
    
    check_credit = fields.Boolean('Check Credit')
    credit_limit_on_hold  = fields.Boolean('Credit limit on hold')
    credit_limit = fields.Float('Credit Limit')
    is_credit_group = fields.Boolean('Credit Group', compute='_check_credit_config_group')
    
    
    def _check_credit_config_group(self):
        for partner in self:
            if self.env.user.has_group('dev_customer_credit_limit.credit_limit_config'):
                partner.is_credit_group = True
            else:
                partner.is_credit_group = False

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
