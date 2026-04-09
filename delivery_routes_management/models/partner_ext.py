from odoo import fields, models

class Partner(models.Model):
    _inherit = "res.partner"

    salesregion_id = fields.Many2one(
        comodel_name="delivery.sales.region",
        string="Sales Region",
        index=True,
        ondelete="set null",
        help="(365 custom) Select the main delivery region. e.g., Central, Northern, Southern.",
    )
    subregion_id = fields.Many2one(
        comodel_name="delivery.sub.region",
        string="Subregion",
        index=True,
        ondelete="set null",
        help="(365 custom) Select a more specific area within the chosen region. e.g., Upper North, Inner Bangkok.",
    )