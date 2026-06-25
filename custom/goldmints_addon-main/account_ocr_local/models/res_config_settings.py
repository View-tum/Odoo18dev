from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    local_ocr_enabled = fields.Boolean(
        string="Enable Local OCR",
        config_parameter="account_ocr_local.local_ocr_enabled",
        default=False,
    )
    local_ocr_server_url = fields.Char(
        string="Local OCR Server URL",
        config_parameter="account_ocr_local.local_ocr_server_url",
        default="http://127.0.0.1:8099",
    )
    local_ocr_timeout = fields.Integer(
        string="Local OCR Timeout",
        config_parameter="account_ocr_local.local_ocr_timeout",
        default=30,
    )
    local_ocr_confidence_threshold = fields.Float(
        string="Minimum OCR Confidence",
        config_parameter="account_ocr_local.local_ocr_confidence_threshold",
        default=0.90,
    )
    local_ocr_replace_lines = fields.Boolean(
        string="Replace Existing Invoice Lines",
        config_parameter="account_ocr_local.local_ocr_replace_lines",
        default=False,
    )
