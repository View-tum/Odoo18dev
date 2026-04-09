from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request

class WebsiteSaleApproval(WebsiteSale):

    def _checkout_form_save(self, mode, checkout, all_values):
        # Tag the env context so partner creation auto-approves & marks ecom_exempt
        ctx = dict(request.env.context, from_website=True, website_id=getattr(request.website, 'id', False))
        request.env.context = ctx
        return super()._checkout_form_save(mode, checkout, all_values)
