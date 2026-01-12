# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    sh_enable_approval = fields.Boolean("Enable Approval work Flow")
    sh_restrict_for_close_period = fields.Boolean(
        "Restrict record creation for Closed Fiscal Period or Closed Fiscal Year"
    )
