from odoo import fields, models

class DeliveryRoute(models.Model):
    _name = "delivery.route"
    _description = "Delivery Route"
    _order = "name asc"

    route_code = fields.Integer(
        string="Route Code",
        required=True,
        index=True,
        help="(365 custom) Enter a unique code for the delivery route. E.g., 'RTE-BKK-01'."
    )
    name = fields.Char(
        string="Route Name",
        required=True,
        help="(365 custom) A descriptive name for the route, e.g., 'Bangkok Downtown Morning Route'."
    )
    route_description = fields.Char(
        string="Route Description",
        help="(365 custom) Provide more details about the route, such as the areas covered, delivery schedule, or specific instructions."
    )
    vehicle_plateno = fields.Char(
        string="Vehicle Plate No",
        help="(365 custom) Select the vehicle assigned to this delivery route."
    )
    responsible = fields.Char(
        string="Responsible",
        help="(365 custom) Select the user or employee responsible for managing this route."
    )
    responsible_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Responsible",
        help="(365 custom) Assign the user who is the main point of contact for this route. This person typically manages the schedule and resolves delivery issues."
    )
    subregion_ids = fields.One2many(
        comodel_name="delivery.sub.region",
        inverse_name="route_id",
        string="Subregions",
        help="(365 custom) Link all subregions that are part of this delivery route. This helps organize deliveries for specific smaller areas."
    )

    _sql_constraints = [
        ("route_code_unique", "unique(route_code)", "Route code must be unique."),
    ]