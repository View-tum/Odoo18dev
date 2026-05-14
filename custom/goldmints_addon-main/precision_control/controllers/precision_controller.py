from odoo import http
from odoo.http import request
from odoo.addons.precision_control.models.precision_patch import _get_precision


class PrecisionController(http.Controller):

    @http.route('/precision_control/get_settings', type='json', auth='user')
    def get_precision_settings(self):
        return {
            'sale': _get_precision(request.env, 'sale'),
            'purchase': _get_precision(request.env, 'purchase'),
            'mrp': _get_precision(request.env, 'mrp'),
            'account': _get_precision(request.env, 'account'),
            'expense': _get_precision(request.env, 'expense'),
            'stock': _get_precision(request.env, 'stock'),
            'product': _get_precision(request.env, 'product'),
        }
