from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ui_icon_scale = fields.Float(
        string="UI Icon Scale",
        config_parameter='custom_ui_icon_scale.scale',
        default=1.0,
        help="Adjust the size of Save and Cancel icons (e.g. 1.2 for 20% larger)"
    )
    ui_icon_spacing = fields.Float(
        string="UI Icon Spacing (px)",
        config_parameter='custom_ui_icon_scale.spacing',
        default=0.0,
        help="Adjust the horizontal spacing between icons in pixels."
    )
