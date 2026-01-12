from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.constrains('partner_id')
    def _check_partner_approved(self):
        for order in self:
            partner = order.partner_id
            if not partner:
                continue
            # Allow if partner is approved OR e-commerce exempt OR this is a website order
            if partner.approval_state == 'approved' or partner.ecom_exempt or order.website_id:
                continue
            raise ValidationError(_("Selected customer is not approved yet."))
        
        
    @api.constrains('product_id')
    def _check_product_approved(self):
        for line in self:
            product = line.product_id
            if not product:
                continue
            tmpl = product.product_tmpl_id
            if tmpl.approval_state != 'approved':
                raise ValidationError(_("Product '%s' is not approved yet.") % (tmpl.display_name,))
