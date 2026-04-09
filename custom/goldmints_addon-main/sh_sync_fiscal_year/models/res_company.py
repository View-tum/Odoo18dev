# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    sh_enable_approval = fields.Boolean("Enable Approval work Flow")
    sh_restrict_for_close_period = fields.Boolean(
        "Restrict record creation for Closed Fiscal Period or Closed Fiscal Year"
    )
    sh_only_current_period_open = fields.Boolean(
        "Open Current Period Only",
        default=True,
        help="When enabled, newly generated periods are opened only for the current month; past and future months start as closed.",
    )
    sh_auto_close_future_periods = fields.Boolean(
        "Auto Close Future Periods",
        default=True,
        help="When enabled, generated future periods are created in Closed state.",
    )
    sh_sync_odoo_lock_dates = fields.Boolean(
        "Sync Odoo Global Lock Date from Closed Periods",
        default=True,
        help="Synchronize the company Global Lock Date with the latest closed fiscal period.",
    )
