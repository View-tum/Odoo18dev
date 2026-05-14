from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    manufacturing_type = fields.Selection(
        [
            ("plastic", "Plastic"),
            ("pharma", "Pharma"),
            ("packaging", "Packaging"),
        ],
        string="Manufacturing Type",
        help="Indicates whether this product is manufactured in the Plastic, Pharma, or Packaging factory.",
    )

    x_important_notify = fields.Boolean(
        string="Notify Production Important",
        help="If checked, a popup alert will be sent to the selected users "
        "when this product is part of an International Sales Order.",
    )

    def _has_sm_internal_reference(self):
        self.ensure_one()
        codes = self.product_variant_ids.mapped("default_code")
        return any((code or "").upper().startswith("SM") for code in codes)

    @api.model
    def _get_sm_pharma_route_commands(self, template=False):
        Route = self.env["stock.route"]
        routes_to_remove = Route.search([
            ("name", "in", ["Auto Transfer Semi (Plastic)", "Manufacture (Pharma)"])
        ])
        routes_to_add = Route.search([
            ("name", "in", ["Auto Transfer Semi (Pharma)", "Manufacture (Plastic)"])
        ])

        commands = []
        if template:
            commands.extend((3, route.id) for route in routes_to_remove & template.route_ids)
            commands.extend((4, route.id) for route in routes_to_add - template.route_ids)
        else:
            commands.extend((3, route.id) for route in routes_to_remove)
            commands.extend((4, route.id) for route in routes_to_add)
        return commands

    def _apply_sm_pharma_policy(self):
        templates = self.filtered(lambda template: template._has_sm_internal_reference())
        for template in templates:
            vals = {"manufacturing_type": "plastic"}
            route_commands = template._get_sm_pharma_route_commands(template=template)
            if route_commands:
                vals["route_ids"] = route_commands
            template.with_context(skip_sm_pharma_policy=True).write(vals)
        return True

    @api.model
    def _sync_sm_products_to_pharma(self):
        products = self.env["product.product"].search([("default_code", "=like", "SM%")])
        products.product_tmpl_id._apply_sm_pharma_policy()
        return True

    @api.model_create_multi
    def create(self, vals_list):
        templates = super().create(vals_list)
        if not self.env.context.get("skip_sm_pharma_policy"):
            templates._apply_sm_pharma_policy()
        return templates

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get("skip_sm_pharma_policy"):
            self._apply_sm_pharma_policy()
        return res

