from odoo import fields, models

class SubRegion(models.Model):
    _name = "delivery.sub.region"
    _description = "Subregion"
    _order = "name asc"

    code = fields.Integer(
        string="Subregion Code",
        required=True,
        index=True,
        help="(365 custom) Enter a unique code for the subregion. E.g., 'BKK-SATHORN'."
    )
    name = fields.Char(
        string="Subregion Name",
        required=True,
        help="(365 custom) The full name of the subregion, e.g., 'Sathorn District'."
    )
    description = fields.Char(
        string="Description",
        help="(365 custom) Provide more details about the subregion, such as major roads, landmarks, or specific boundaries."
    )

    route_id = fields.Many2one(
        comodel_name="delivery.route",
        string="Route",
        required=True,
        ondelete="restrict",
        index=True,
        help="(365 custom) Select the delivery route that covers this subregion."
    )

    _sql_constraints = [
        ("subregion_code_unique", "unique(code)", "Subregion code must be unique."),
    ]