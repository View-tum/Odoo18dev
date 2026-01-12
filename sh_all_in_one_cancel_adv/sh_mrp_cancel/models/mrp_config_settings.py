# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    mrp_operation_type = fields.Selection([('cancel', 'Cancel'), ('cancel_draft', 'Cancel and Reset to Draft'), ('cancel_delete', 'Cancel and Delete')],
                                          default='cancel', string="Opration Type")
    cancel_child_mo = fields.Boolean(string="Cancel Child Manufacturing Orders")

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    mrp_operation_type = fields.Selection(
        string="Opration Type", default=lambda self: self.env.user.company_id.mrp_operation_type, related="company_id.mrp_operation_type", readonly=False)
    cancel_child_mo = fields.Boolean(string="Cancel Child Manufacturing Orders",related="company_id.cancel_child_mo",readonly=False)