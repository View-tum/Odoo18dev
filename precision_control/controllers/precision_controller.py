from odoo import http
from odoo.http import request


class PrecisionController(http.Controller):

    @http.route('/precision_control/get_settings', type='json', auth='user')
    def get_precision_settings(self):
        ICP = request.env['ir.config_parameter'].sudo()
        return {
            'sale': int(ICP.get_param('precision_control.precision_sale', 2)),
            'purchase': int(ICP.get_param('precision_control.precision_purchase', 3)),
            'mrp': int(ICP.get_param('precision_control.precision_mrp', 4)),
            'account': int(ICP.get_param('precision_control.precision_account', 2)),
            'stock': int(ICP.get_param('precision_control.precision_stock', 6)),
            'product': int(ICP.get_param('precision_control.precision_product', 6)),
        }
