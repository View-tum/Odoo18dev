# -*- coding: utf-8 -*-

from odoo import api, fields, models


def _column_exists(cr, table_name, column_name):
    cr.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = %s AND column_name = %s
        LIMIT 1
        """,
        (table_name, column_name),
    )
    return bool(cr.fetchone())


class ProductTemplate(models.Model):
    _inherit = "product.template"

    company_currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        readonly=True,
        string="Company Currency",
    )

    # Do NOT rename core field standard_price. Use an alias instead.
    # Alias of standard_price with the same value, editable, and stored.
    cost_per_unit = fields.Monetary(
        string="Cost per Unit",
        currency_field="company_currency_id",
        compute="_compute_standard_piece",
        inverse="_inverse_standard_piece",
        store=True,
        readonly=False,
        help="Alias of Standard Price used by price guard logic.",
    )

    upcharge_percent = fields.Float(
        string="Upcharge (%)",
        digits="Product Price",
        help="Percent added on top of the Cost per Unit to form the final allowed price.",
        company_dependent=True,
    )

    final_allowed_price = fields.Monetary(
        string="Final Allowed Price",
        currency_field="company_currency_id",
        compute="_compute_final_allowed_price",
        store=True,
        readonly=True,
        help="Computed as Cost per Unit * (1 + Upcharge% / 100). Used to guard purchase order unit prices.",
    )

    @api.depends("standard_price")
    def _compute_standard_piece(self):
        for template in self:
            # Mirror core standard_price to our alias
            template.cost_per_unit = template.standard_price or 0.0

    def _inverse_standard_piece(self):
        for template in self:
            # Write back to core field to keep them in sync
            template.standard_price = template.cost_per_unit or 0.0

    @api.depends("cost_per_unit", "upcharge_percent")
    def _compute_final_allowed_price(self):
        for template in self:
            standard_piece = template.cost_per_unit or 0.0
            upcharge_percent = template.upcharge_percent or 0.0
            template.final_allowed_price = standard_piece * (1.0 + (upcharge_percent / 100.0))

    def _auto_init(self):
        res = super()._auto_init()
        cr = self.env.cr
        if _column_exists(cr, "product_template", "standard_piece") and _column_exists(
            cr, "product_template", "cost_per_unit"
        ):
            cr.execute(
                """
                UPDATE product_template
                SET cost_per_unit = standard_piece
                WHERE cost_per_unit IS NULL
                """
            )
        return res
