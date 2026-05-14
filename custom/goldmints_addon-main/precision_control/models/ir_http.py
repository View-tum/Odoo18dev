from odoo import models
from .precision_patch import _get_precision


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        result = super(IrHttp, self).session_info()
        result['precision_settings'] = {
            'sale': _get_precision(self.env, 'sale'),
            'purchase': _get_precision(self.env, 'purchase'),
            'mrp': _get_precision(self.env, 'mrp'),
            'account': _get_precision(self.env, 'account'),
            'expense': _get_precision(self.env, 'expense'),
            'stock': _get_precision(self.env, 'stock'),
            'product': _get_precision(self.env, 'product'),
        }
        return result
