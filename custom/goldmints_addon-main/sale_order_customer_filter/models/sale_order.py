from lxml import etree
from odoo import api, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _get_allowed_customer_domain(self):
        domain = super()._get_allowed_customer_domain() if hasattr(super(), '_get_allowed_customer_domain') else [('active', '=', True)]
        clean_filter = [
            
            '|', ('type', '=', 'contact'), ('type', '=', False)
        ]
        return domain + clean_filter
    
    #Allow parent_id True becasue will use parent_id as a company group
    # '|', ('parent_id', '=', False), ('is_company', '=', True),

    # @api.onchange('partner_id')
    # def onchange_partner_id_warning(self):
    #     """ Provide a non-blocking warning if the customer has no Tax ID. """
    #     if self.partner_id and not self.partner_id.vat:
    #         return {
    #             'warning': {
    #                 'title': _("Missing Tax ID"),
    #                 'message': _("Customer '%s' has no Tax ID. Please verify.") % self.partner_id.name,
    #             }
    #         }

    @api.model
    def get_views(self, views, options=None):
        result = super().get_views(views, options=options)

        form_view = result.get("views", {}).get("form")
        if form_view and form_view.get("arch"):
            doc = etree.fromstring(form_view["arch"])

            # 1. Update Customer Domain
            domain = str(self.env['sale.order']._get_allowed_customer_domain())
            for node in doc.xpath("//field[@name='partner_id']"):
                node.set("domain", domain)

            # 2. Update Address Domains (Include the partner itself + child addresses)
            # Using commercial_partner_id to ensure we see addresses belonging to the same business entity
            invoice_domain = "['|', ('id', '=', partner_id), '&', ('commercial_partner_id', '=', partner_id), ('type', '=', 'invoice')]"
            shipping_domain = "['|', ('id', '=', partner_id), '&', ('commercial_partner_id', '=', partner_id), ('type', '=', 'delivery')]"

            for node in doc.xpath("//field[@name='partner_invoice_id']"):
                node.set("domain", invoice_domain)
            for node in doc.xpath("//field[@name='partner_shipping_id']"):
                node.set("domain", shipping_domain)

            form_view["arch"] = etree.tostring(doc, encoding="unicode")

        return result
