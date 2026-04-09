import json

from odoo import api, models

PRECISION_DEFAULTS = {
    'sale': 2,
    'purchase': 3,
    'mrp': 4,
    'account': 2,
    'stock': 6,
    'product': 6,
}


def _get_precision(env, module_key):
    param_name = f'precision_control.precision_{module_key}'
    value = env['ir.config_parameter'].sudo().get_param(param_name, default=PRECISION_DEFAULTS.get(module_key, 2))
    try:
        return int(value)
    except (ValueError, TypeError):
        return PRECISION_DEFAULTS.get(module_key, 2)


def _inject_precision(arch_tree, precision):
    for node in arch_tree.xpath("//field[@name]"):
        node.set('digits', f'[16, {precision}]')

        options = node.get('options')
        if options:
            try:
                options_dict = json.loads(options)
            except (ValueError, TypeError):
                options_dict = {}
        else:
            options_dict = {}

        options_dict['digits'] = [16, precision]
        node.set('options', json.dumps(options_dict))

    return arch_tree


class SaleOrderPrecision(models.Model):
    _inherit = 'sale.order'

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id=view_id, view_type=view_type, **options)
        precision = _get_precision(self.env, 'sale')
        arch = _inject_precision(arch, precision)
        return arch, view


class PurchaseOrderPrecision(models.Model):
    _inherit = 'purchase.order'

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id=view_id, view_type=view_type, **options)
        precision = _get_precision(self.env, 'purchase')
        arch = _inject_precision(arch, precision)
        return arch, view


class PurchaseRequestPrecision(models.Model):
    _inherit = 'purchase.request'

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id=view_id, view_type=view_type, **options)
        precision = _get_precision(self.env, 'purchase')
        arch = _inject_precision(arch, precision)
        return arch, view


class MrpProductionPrecision(models.Model):
    _inherit = 'mrp.production'

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id=view_id, view_type=view_type, **options)
        precision = _get_precision(self.env, 'mrp')
        arch = _inject_precision(arch, precision)
        return arch, view


class AccountMovePrecision(models.Model):
    _inherit = 'account.move'

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id=view_id, view_type=view_type, **options)
        precision = _get_precision(self.env, 'account')
        arch = _inject_precision(arch, precision)
        return arch, view


class StockPickingPrecision(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id=view_id, view_type=view_type, **options)
        precision = _get_precision(self.env, 'stock')
        arch = _inject_precision(arch, precision)
        return arch, view


class ProductTemplatePrecision(models.Model):
    _inherit = 'product.template'

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id=view_id, view_type=view_type, **options)
        precision = _get_precision(self.env, 'product')
        arch = _inject_precision(arch, precision)
        return arch, view
