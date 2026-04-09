from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        result = super(IrHttp, self).session_info()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        result['precision_settings'] = {
            'sale': int(get_param('precision_control.precision_sale', '2')),
            'purchase': int(get_param('precision_control.precision_purchase', '3')),
            'mrp': int(get_param('precision_control.precision_mrp', '4')),
            'account': int(get_param('precision_control.precision_account', '2')),
            'expense': int(get_param('precision_control.precision_expense', '2')),
            'stock': int(get_param('precision_control.precision_stock', '2')),
            'product': int(get_param('precision_control.precision_product', '2')),
        }
        return result
