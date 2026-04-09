from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.constrains('partner_id')
    def _check_partner_approved(self):
        for order in self:
            if order.env.user.has_group('sales_team.group_sale_manager'):
                continue
            partner = order.partner_id
            if not partner:
                continue
            # Allow if partner is approved OR e-commerce exempt OR this is a website order.
            # website_id exists only if website_sale is installed, so guard the access.
            is_website_order = False
            if 'website_id' in order._fields:
                is_website_order = bool(order.website_id)
            else:
                ctx = order.env.context
                is_website_order = bool(ctx.get('website_id') or ctx.get('from_website'))
            if partner.approval_state == 'approved' or partner.ecom_exempt or is_website_order:
                continue
            raise ValidationError(_("Selected customer is not approved yet."))
        
        
    @api.constrains('order_line')
    def _check_product_approved(self):
        for order in self:
            for line in order.order_line:
                product = line.product_id
                if not product:
                    continue
                tmpl = product.product_tmpl_id
                if tmpl.approval_state != 'approved':
                    raise ValidationError(_("Product '%s' is not approved yet.") % (tmpl.display_name,))
