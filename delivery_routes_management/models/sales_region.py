from odoo import fields, models

class SalesRegion(models.Model):
    _name = "delivery.sales.region"
    _description = "Sales Region"
    _order = "name asc"

    code = fields.Integer(
        string="Region Code", 
        required=True, 
        index=True,
        help="(365 custom) Enter a unique code for the sales region. E.g., 'NA' for North America or '77' for Bangkok."
    )
    name = fields.Char(
        string="Region Name",
        required=True,
        help="(365 custom) The full name of the sales region."
    )
    description = fields.Char(
        string="Description",
        help="(365 custom) detailed description of the sales region, including boundaries or specific notes."
    )

    _sql_constraints = [
        ("region_code_unique", "unique(code)", "Region code must be unique."),
    ]