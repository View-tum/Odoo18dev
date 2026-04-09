from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    mo_auto_merge_enabled = fields.Boolean(
        string="Auto Merge MOs",
        config_parameter='mrp_auto_merge.enabled',
        default=True,
    )
    mo_merge_date_range = fields.Integer(
        string="Merge Date Range (Days)",
        config_parameter='mrp_auto_merge.date_range',
        default=7,
        help="MOs within this date range will be merged together",
    )
