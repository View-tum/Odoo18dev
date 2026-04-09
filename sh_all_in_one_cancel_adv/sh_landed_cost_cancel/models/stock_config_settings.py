# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    landed_cost_operation_type = fields.Selection([('cancel', 'Cancel'), ('cancel_draft', 'Cancel and Reset to Draft'), ('cancel_delete', 'Cancel and Delete')],
                                                  default='cancel', string="Opration Type")


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    landed_cost_operation_type = fields.Selection(string="Opration Type", default=lambda self: self.env.user.company_id.landed_cost_operation_type, related="company_id.landed_cost_operation_type", readonly=False)
