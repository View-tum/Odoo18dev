from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = "sale.order"

    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Salesperson",
        domain="[('sale_team_id', '=', team_id)]",
    )
