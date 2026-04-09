from odoo import models, fields


class MrpWorkcenter(models.Model):
    _inherit = "mrp.workcenter"

    manufacturing_type = fields.Selection(
        [
            ("plastic", "Plastic"),
            ("pharma", "Pharma"),
            ("packaging", "Packaging"),
        ],
        string="Manufacturing Type",
        help="Indicates whether this workcenter belongs to the Plastic, Pharma, or Packaging factory.",
    )
