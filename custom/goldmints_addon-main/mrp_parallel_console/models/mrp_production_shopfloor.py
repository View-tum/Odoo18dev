from odoo import api, fields, models


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    hide_from_shopfloor = fields.Boolean(
        string="Hide from Shopfloor",
        default=True,
        tracking=True,
        help="If checked, this Manufacturing Order will not appear on the Shopfloor Console.",
    )
    show_on_shopfloor = fields.Boolean(
        string="Show in Shopfloor",
        compute="_compute_show_on_shopfloor",
        inverse="_inverse_show_on_shopfloor",
        store=True,
        readonly=False,
        help="Controls whether this Manufacturing Order is visible in the Shopfloor Console.",
    )

    @api.depends("hide_from_shopfloor")
    def _compute_show_on_shopfloor(self):
        for production in self:
            production.show_on_shopfloor = not production.hide_from_shopfloor

    def _inverse_show_on_shopfloor(self):
        for production in self:
            production.hide_from_shopfloor = not production.show_on_shopfloor

    def action_show_on_shopfloor(self):
        self.write({"hide_from_shopfloor": False})

    def action_hide_from_shopfloor(self):
        self.write({"hide_from_shopfloor": True})
