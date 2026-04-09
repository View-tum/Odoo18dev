from lxml import etree

from odoo import api, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _get_allowed_customer_domain(self):
        """Build the customer domain without fetching every partner upfront."""
        user = self.env.user
        # Match the active_test=True behavior (True or unset)
        domain = [("active", "!=", False)]

        if not (user.has_group("base.group_system") or user.has_group("sales_team.group_sale_manager")):
            domain.append(("customer_rank", ">", 0))
            if user.has_group("sales_team.group_sale_salesman") or user.has_group(
                "sales_team.group_sale_salesman_all_leads"
            ):
                domain.extend(
                    ["|", ("user_id", "=", user.id), ("commercial_partner_id.user_id", "=", user.id)]
                )

        return domain

    @api.model
    def get_views(self, views, options=None):
        """Inject the allowed customer domain into the form view."""
        result = super().get_views(views, options=options)

        form_view = result.get("views", {}).get("form")
        if form_view and form_view.get("arch"):
            doc = etree.fromstring(form_view["arch"])
            domain = str(self._get_allowed_customer_domain())

            for node in doc.xpath("//field[@name='partner_id']"):
                node.set("domain", domain)

            form_view["arch"] = etree.tostring(doc, encoding="unicode")

        return result
