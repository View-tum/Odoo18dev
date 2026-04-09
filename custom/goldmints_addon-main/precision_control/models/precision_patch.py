import ast
import json

from lxml import etree
from odoo import api, models
from odoo.tools.misc import NON_BREAKING_SPACE, formatLang

PRECISION_DEFAULTS = {
    'sale': 2,
    'purchase': 3,
    'mrp': 4,
    'account': 2,
    'expense': 2,
    'stock': 2,
    'product': 2,
}

NUMERIC_KEYWORDS = (
    'amount', 'total', 'price', 'balance', 'residual', 'subtotal', 'untaxed', 'taxed',
    'qty', 'quantity', 'quant', 'debit', 'credit', 'rate', 'discount', 'cost',
    'unit', 'uom', 'margin', 'weight', 'volume',
)


def _get_precision_key_from_model(model_name, context=None):
    if not model_name:
        return None
    model_name = str(model_name)
    context = context or {}

    if model_name in ('stock.move', 'stock.move.line'):
        params = context.get('params') or {}
        active_model = context.get('active_model') or params.get('model') or params.get('res_model')
        if active_model in ('purchase.order', 'purchase.request'):
            return 'purchase'
        if active_model == 'sale.order':
            return 'sale'
        if active_model in ('mrp.production', 'mrp.workorder'):
            return 'mrp'

    if model_name.startswith('purchase.request'):
        return 'purchase'
    if model_name.startswith('purchase.'):
        return 'purchase'
    if model_name.startswith('sale.'):
        return 'sale'
    if model_name.startswith('mrp.'):
        return 'mrp'
    if model_name.startswith('stock.'):
        return 'stock'
    if model_name.startswith('product.'):
        return 'product'
    if model_name.startswith('account.'):
        return 'account'
    if model_name.startswith('hr.expense'):
        return 'expense'
    return None


def _get_precision_key_from_context(env, fallback_model=None):
    context = env.context
    module_key = context.get('precision_module')
    if module_key in PRECISION_DEFAULTS:
        return module_key

    params = context.get('params') or {}
    model_hints = [
        fallback_model,
        context.get('precision_model'),
        context.get('active_model'),
        context.get('model'),
        context.get('default_res_model'),
        params.get('model'),
        params.get('res_model'),
    ]
    for model_name in model_hints:
        module_key = _get_precision_key_from_model(model_name, context)
        if module_key in PRECISION_DEFAULTS:
            return module_key
    return None

def _get_precision(env, module_key):
    param_name = f'precision_control.precision_{module_key}'
    value = env['ir.config_parameter'].sudo().get_param(param_name, default=PRECISION_DEFAULTS.get(module_key, 2))
    try:
        return int(value)
    except (ValueError, TypeError):
        return PRECISION_DEFAULTS.get(module_key, 2)

def _parse_options(options):
    if not options:
        return {}
    try:
        parsed = json.loads(options)
        if isinstance(parsed, dict):
            return parsed
    except (ValueError, TypeError):
        pass
    try:
        parsed = ast.literal_eval(options)
        if isinstance(parsed, dict):
            return parsed
    except (ValueError, SyntaxError, TypeError):
        pass
    return {}

def _is_numeric_field(field, node):
    if field:
        return field.type in ('float', 'monetary')
    widget = (node.get('widget') or '').lower()
    if widget in ('monetary', 'float', 'float_time', 'monetary_field', 'percentage', 'percent'):
        return True
    field_name = (node.get('name') or '').lower()
    if 'currency_id' in field_name:
        return True
    return any(kw in field_name for kw in NUMERIC_KEYWORDS)

def _apply_precision(node, precision, precision_key):
    node.set('digits', f'[16, {precision}]')
    options_dict = _parse_options(node.get('options'))
    options_dict['digits'] = [16, precision]
    options_dict['decimal_precision'] = precision
    options_dict['field_digits'] = True
    options_dict['precision_type'] = precision_key
    node.set('options', json.dumps(options_dict))

def _inject_precision(arch_tree, precision_key, model):
    precision = _get_precision(model.env, precision_key)

    def walk(node, current_model):
        if node.tag == 'field':
            field_name = node.get('name')
            field = current_model._fields.get(field_name) if (current_model and field_name) else None
            if _is_numeric_field(field, node):
                _apply_precision(node, precision, precision_key)
            if field and field.type in ('one2many', 'many2many'):
                try:
                    comodel = model.env[field.comodel_name]
                except KeyError:
                    comodel = None
                if comodel:
                    for child in node:
                        walk(child, comodel)
                    return
        for child in node:
            walk(child, current_model)

    walk(arch_tree, model)
    return arch_tree

def _ensure_field_in_view(arch_tree, field_name):
    if arch_tree.tag in ('tree', 'list', 'form', 'kanban', 'activity') and arch_tree.find(f".//field[@name='{field_name}']") is None:
        field = etree.Element('field', {'name': field_name, 'invisible': '1'})
        arch_tree.insert(0, field)
    return arch_tree


class UniversalPrecisionView(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id=view_id, view_type=view_type, **options)
        if view_type not in ('form', 'tree', 'list', 'kanban', 'activity'):
            return arch, view
        precision_key = _get_precision_key_from_context(self.env, self._name)
        if precision_key:
            arch = _inject_precision(arch, precision_key, self)
        return arch, view

class SaleOrderPrecision(models.Model):
    _inherit = 'sale.order'
    def _compute_tax_totals(self):
        super(SaleOrderPrecision, self.with_context(precision_module='sale'))._compute_tax_totals()
    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id=view_id, view_type=view_type, **options)
        arch = _inject_precision(arch, 'sale', self)
        return arch, view

class PurchaseOrderPrecision(models.Model):
    _inherit = 'purchase.order'
    def _compute_tax_totals(self):
        super(PurchaseOrderPrecision, self.with_context(precision_module='purchase'))._compute_tax_totals()
    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id=view_id, view_type=view_type, **options)
        arch = _inject_precision(arch, 'purchase', self)
        return arch, view

class AccountMovePrecision(models.Model):
    _inherit = 'account.move'
    def _compute_tax_totals(self):
        for move in self:
            super(AccountMovePrecision, move.with_context(precision_module='account'))._compute_tax_totals()
    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id=view_id, view_type=view_type, **options)
        arch = _inject_precision(arch, 'account', self)
        return arch, view

class AccountMoveLinePrecision(models.Model):
    _inherit = 'account.move.line'
    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id=view_id, view_type=view_type, **options)
        arch = _inject_precision(arch, 'account', self)
        return arch, view

class AccountTaxPrecision(models.Model):
    _inherit = 'account.tax'
    @api.model
    def _get_tax_totals_summary(self, base_lines, currency, company, cash_rounding=None):
        res = super()._get_tax_totals_summary(base_lines, currency, company, cash_rounding=cash_rounding)
        module = self.env.context.get('precision_module', 'account')
        precision = _get_precision(self.env, module)
        res['currency_pd'] = 10**-precision
        res['company_currency_pd'] = 10**-precision
        return res

class ResCurrencyPrecision(models.Model):
    _inherit = 'res.currency'

    def format(self, amount):
        self.ensure_one()
        precision_module = _get_precision_key_from_context(self.env)
        if precision_module:
            precision = _get_precision(self.env, precision_module)
            formatted_amount = formatLang(self.env, amount + 0.0, digits=precision)
            if not self.symbol:
                return formatted_amount
            if self.position == 'before':
                return f"{self.symbol}{NON_BREAKING_SPACE}{formatted_amount}"
            return f"{formatted_amount}{NON_BREAKING_SPACE}{self.symbol}"
        return super().format(amount)

class AccountJournalPrecision(models.Model):
    _inherit = 'account.journal'

    def _get_journal_dashboard_data_batched(self):
        return super(AccountJournalPrecision, self.with_context(precision_module='account'))._get_journal_dashboard_data_batched()

class AccountPaymentPrecision(models.Model):
    _inherit = 'account.payment'

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id=view_id, view_type=view_type, **options)
        arch = _inject_precision(arch, 'account', self)
        return arch, view

class AccountPaymentRegisterPrecision(models.TransientModel):
    _inherit = 'account.payment.register'

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id=view_id, view_type=view_type, **options)
        arch = _inject_precision(arch, 'account', self)
        return arch, view

class GenericPrecisionOverride(models.AbstractModel):
    _name = 'precision.control.override'
    _description = 'Generic Precision Override'
    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id=view_id, view_type=view_type, **options)
        key = 'account'
        if self._name.startswith('sale.'):
            key = 'sale'
        elif self._name.startswith('purchase.'):
            key = 'purchase'
        elif self._name.startswith('mrp.'):
            key = 'mrp'
        elif self._name.startswith('stock.'):
            key = 'stock'
        elif self._name.startswith('product.'):
            key = 'product'
        elif self._name.startswith('hr.expense'):
            key = 'expense'
        arch = _inject_precision(arch, key, self)
        return arch, view

class SaleOrderLinePrecision(models.Model):
    _inherit = 'sale.order.line'
    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id=view_id, view_type=view_type, **options)
        arch = _inject_precision(arch, 'sale', self)
        return arch, view

class PurchaseOrderLinePrecision(models.Model):
    _inherit = 'purchase.order.line'
    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id=view_id, view_type=view_type, **options)
        arch = _inject_precision(arch, 'purchase', self)
        return arch, view

class StockMovePrecision(models.Model):
    _inherit = 'stock.move'
    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id=view_id, view_type=view_type, **options)
        key = 'stock'
        active_model = self.env.context.get('active_model')
        if active_model in ('purchase.order', 'purchase.request'):
            key = 'purchase'
        elif active_model == 'sale.order':
            key = 'sale'
        elif active_model in ('mrp.production', 'mrp.workorder'):
            key = 'mrp'
        arch = _inject_precision(arch, key, self)
        return arch, view

class StockMoveLinePrecision(models.Model):
    _inherit = 'stock.move.line'
    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id=view_id, view_type=view_type, **options)
        key = 'stock'
        active_model = self.env.context.get('active_model')
        if active_model in ('purchase.order', 'purchase.request'):
            key = 'purchase'
        elif active_model == 'sale.order':
            key = 'sale'
        elif active_model in ('mrp.production', 'mrp.workorder'):
            key = 'mrp'
        arch = _inject_precision(arch, key, self)
        return arch, view

class StockQuantPrecision(models.Model):
    _inherit = 'stock.quant'
    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id=view_id, view_type=view_type, **options)
        arch = _inject_precision(arch, 'stock', self)
        return arch, view

class MrpProductionPrecision(models.Model):
    _inherit = 'mrp.production'
    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id=view_id, view_type=view_type, **options)
        arch = _inject_precision(arch, 'mrp', self)
        return arch, view

class MrpProductionLinePrecision(models.Model):
    _inherit = 'mrp.bom.line'
    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id=view_id, view_type=view_type, **options)
        arch = _inject_precision(arch, 'mrp', self)
        return arch, view

class StockPickingPrecision(models.Model):
    _inherit = 'stock.picking'
    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id=view_id, view_type=view_type, **options)
        arch = _inject_precision(arch, 'stock', self)
        return arch, view

class ProductProductPrecision(models.Model):
    _inherit = 'product.product'
    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id=view_id, view_type=view_type, **options)
        arch = _inject_precision(arch, 'product', self)
        return arch, view

class ProductTemplatePrecision(models.Model):
    _inherit = 'product.template'
    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id=view_id, view_type=view_type, **options)
        arch = _inject_precision(arch, 'product', self)
        return arch, view

class PurchaseRequestPrecision(models.Model):
    _inherit = 'purchase.request'
    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id=view_id, view_type=view_type, **options)
        arch = _inject_precision(arch, 'purchase', self)
        return arch, view

class MrpWorkorderPrecision(models.Model):
    _inherit = 'mrp.workorder'
    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id=view_id, view_type=view_type, **options)
        arch = _inject_precision(arch, 'mrp', self)
        return arch, view

class PurchaseRequestLinePrecision(models.Model):
    _inherit = 'purchase.request.line'
    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id=view_id, view_type=view_type, **options)
        arch = _inject_precision(arch, 'purchase', self)
        return arch, view
