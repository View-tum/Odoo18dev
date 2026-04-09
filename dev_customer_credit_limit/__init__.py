# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle
#
##############################################################################

def pre_init_check(cr):
    from odoo.service import common
    from odoo import api, fields, models, SUPERUSER_ID, _
    from odoo.exceptions import AccessError, UserError, ValidationError
    version_info = common.exp_version()
    server_serie = version_info.get('server_serie')
    if server_serie != '17.0':
        raise UserError(_('''This application can be installed only on Odoo version 17.0'''))
    return True

from . import models
from . import wizard

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: