from odoo import api, fields, models, _
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _inherit = "sale.order"

    # Mirrors current user's sale_admin for use in views
    is_sale_admin = fields.Boolean(
        string="Is Sale Admin (UI)",
        compute="_compute_is_sale_admin",
        readonly=True,
        help="(365 custom) Technical field for the UI, indicating if the current user has 'Sale Admin' permissions. \
            Used to control view elements like the readonly status of the pricelist."
    )

    @api.depends('pricelist_id')  # recompute when user context changes
    def _compute_is_sale_admin(self):
        is_admin = bool(self.env.user.sale_admin)
        for order in self:
            order.is_sale_admin = is_admin