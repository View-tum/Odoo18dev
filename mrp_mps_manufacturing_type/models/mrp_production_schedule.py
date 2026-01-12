from odoo import models, fields


class MrpProductionSchedule(models.Model):
    _inherit = "mrp.production.schedule"

    manufacturing_type = fields.Selection(
        related="product_id.product_tmpl_id.manufacturing_type",
        store=True,
        readonly=True,
    )
