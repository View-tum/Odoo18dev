from odoo import fields, models, api
from odoo.exceptions import ValidationError


class SaleCommissionRule(models.Model):
    _name = "sale.commission.rule"
    _description = "Sale Commission Rule"
    _order = "commission_trigger asc"

    commission_trigger = fields.Selection(
        selection=[
            ("invoice_confirmed", "Invoice Confirmed"),
            ("invoice_paid", "Invoice Partially Paid"),
            ("fully_paid", "Invoice Fully Paid"),
        ],
        string="Commission Trigger",
        required=True,
        help="(365 custom) The event that triggers commission calculation for this rule.",
    )
    region_ids = fields.Many2many(
        comodel_name="delivery.sales.region",
        string="Sales Region",
        help="(365 custom) The sales regions associated with this rule for commission calculations.",
    )
    rate_id = fields.Many2one(
        comodel_name="sale.commission.rate",
        string="Commission Rate",
        help="(365 custom) The commission rate applied for this rule.",
    )

    _sql_constraints = [
        (
            "commission_trigger_unique",
            "unique(commission_trigger)",
            "Commission trigger rule must be unique.",
        ),
    ]

    @api.constrains("region_ids")
    def _check_unique_regions(self):
        for record in self:
            if not record.region_ids:
                continue

            other_rules = self.search([("id", "!=", record.id)])
            used_regions = other_rules.mapped("region_ids")
            duplicates = set(record.region_ids) & set(used_regions)
            if duplicates:
                duplicate_names = ", ".join([r.name for r in duplicates])
                raise ValidationError(
                    f"Cannot save: Region(s) '{duplicate_names}' are already used in another commission rule.\n"
                    "Tip: A sales region can only be assigned to one commission rule (e.g., if assigned to 'Invoice Confirmed', it cannot be assigned to 'Invoice Fully Paid')."
                )
