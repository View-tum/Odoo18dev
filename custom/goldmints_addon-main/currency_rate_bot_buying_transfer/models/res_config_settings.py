from odoo import fields, models

from .res_company import BOT_API_KEY_PARAMETER


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    bot_buying_transfer_api_key = fields.Char(
        string="BOT API Key",
        config_parameter=BOT_API_KEY_PARAMETER,
    )
