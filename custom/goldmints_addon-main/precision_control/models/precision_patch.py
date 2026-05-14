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

PRECISION_FIELD_NAMES = {
    'mrp': {
        'actual_qty',
        'bom_qty',
        'batch_size',
        'blocked_time',
        'byproduct_cost',
        'capacity',
        'console_qty',
        'component_cost',
        'cost_share',
        'cost',
        'cost_actual',
        'cost_estimated',
        'cost_variance',
        'costs_hour',
        'credit',
        'cycle_time',
        'debit',
        'default_capacity',
        'duration_actual',
        'duration_hours',
        'duration_minutes',
        'current_mo_duration_expected',
        'duration',
        'duration_expected',
        'duration_unit',
        'efficiency_variance',
        'employee_costs_hour',
        'employee_ratio',
        'employee_cost_total',
        'extra_cost',
        'forecast_availability',
        'forecast_qty',
        'forecast_target_qty',
        'good_qty',
        'hierarchy_duration_expected',
        'hourly_rate',
        'late_backorder_remaining_qty',
        'max_to_replenish_qty',
        'min_to_replenish_qty',
        'mold_cost',
        'mold_cost_hour',
        'mold_cost_total',
        'new_product_qty',
        'new_qty',
        'oee',
        'oee_target',
        'old_product_qty',
        'operation_cost',
        'original_qty',
        'planned_qty',
        'price_unit',
        'price_variance',
        'product_qty',
        'product_qty_available',
        'product_consumed_qty_uom',
        'product_expected_qty_uom',
        'product_uom_qty',
        'product_virtual_available',
        'produced_qty',
        'productive_time',
        'production_capacity',
        'progress',
        'qty',
        'qty_done',
        'qty_produced',
        'qty_producing',
        'qty_production',
        'qty_reported_from_previous_wo',
        'qty_remaining',
        'qty_to_produce',
        'rate_variance',
        'recorded_qty',
        'replenish_qty',
        'scrap_qty',
        'should_consume_qty',
        'subcontracting_cost',
        'time_cycle',
        'time_cycle_manual',
        'time_efficiency',
        'time_start',
        'time_stop',
        'total_cost',
        'total_cost_actual',
        'total_cost_estimated',
        'total_hours',
        'total_variance',
        'unit_cost',
        'unit_component_cost',
        'unit_factor',
        'unit_cost_actual',
        'unit_cost_std',
        'unit_operation_cost',
        'unit_subcontracting_cost',
        'units_per_hour',
        'upd_product_qty',
        'upd_time_cycle_manual',
        'usage_variance',
        'workcenter_load',
        'quantity',
        'quantity_done',
        'reserved_availability',
    },
    'stock': {
        'additional_landed_cost',
        'added_value',
        'amount_total',
        'availability',
        'available_quantity',
        'avg_cost',
        'base_weight',
        'carrier_price',
        'cost_share',
        'current_quantity_svl',
        'current_value_svl',
        'cycle_time',
        'delay',
        'final_cost',
        'forecast_availability',
        'former_cost',
        'free_qty',
        'height',
        'inventory_diff_quantity',
        'inventory_quantity',
        'inventory_quantity_auto_apply',
        'incoming_qty',
        'max_weight',
        'move_quantity',
        'new_quantity',
        'new_value',
        'new_value_by_qty',
        'outgoing_qty',
        'packaging_length',
        'price_unit',
        'product_packaging_qty',
        'product_packaging_quantity',
        'product_packaging_uom_qty',
        'product_qty_available',
        'product_qty',
        'product_max_qty',
        'product_min_qty',
        'product_uom_qty',
        'product_virtual_available',
        'qty_multiple',
        'qty_on_hand_show',
        'qty_to_order',
        'qty_available',
        'qty_done',
        'quantity_product_uom',
        'quantity',
        'quantity_done',
        'remaining_qty',
        'remaining_value',
        'reserved_availability',
        'reserved_quantity',
        'sale_price',
        'scrap_qty',
        'shipping_volume',
        'shipping_weight',
        'should_consume_qty',
        'standard_price',
        'total_value',
        'unit_factor',
        'unit_cost',
        'value',
        'virtual_available',
        'visibility_days',
        'volume',
        'weight',
        'weight_bulk',
        'width',
        'qty_forecast',
        'qty_on_hand',
        'qty_to_order_manual',
    },
    'product': {
        'avg_cost',
        'available_threshold',
        'base_price',
        'buy_item_qty',
        'cost_per_unit',
        'default_extra_price',
        'discount',
        'excess_qty',
        'extra_price',
        'final_allowed_price',
        'fixed_price',
        'forecasted_quantity',
        'free_qty',
        'free_item_qty',
        'gross_weight',
        'incoming_qty',
        'issued_qty',
        'list_price',
        'lst_price',
        'max_qty',
        'min_qty',
        'min_quantity',
        'mrp_product_qty',
        'net_weight',
        'net_movement_qty',
        'on_hand_qty',
        'outgoing_qty',
        'percent_price',
        'price',
        'price_extra',
        'price_discount',
        'price_markup',
        'price_max_margin',
        'price_min_margin',
        'price_round',
        'price_surcharge',
        'produced_qty',
        'purchased_product_qty',
        'qty',
        'qty_from',
        'qty_to',
        'quantity_svl',
        'quantity',
        'received_qty',
        'qty_available',
        'reordering_max_qty',
        'reordering_min_qty',
        'sales_count',
        'service_upsell_threshold',
        'shortage_qty',
        'standard_price',
        'total_excess_qty',
        'total_issued_qty',
        'total_net_movement_qty',
        'total_on_hand_qty',
        'total_produced_qty',
        'total_received_qty',
        'total_shortage_qty',
        'total_value',
        'transform_factor',
        'upcharge_percent',
        'value_svl',
        'virtual_available',
        'volume',
        'weight',
    },
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
        precision = int(value)
    except (ValueError, TypeError):
        precision = PRECISION_DEFAULTS.get(module_key, 2)
    return max(0, precision)

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

def _is_numeric_field(field, node, precision_key=None):
    field_name = node.get('name') or ''
    allowed_fields = PRECISION_FIELD_NAMES.get(precision_key)
    if allowed_fields is not None:
        if field_name not in allowed_fields:
            return False
        if field is None:
            # Some inherited/nested views lose the exact current model while
            # walking the arch. The whitelist is intentionally numeric, so keep
            # applying the configured display precision when the name matches.
            return True
    if field is not None:
        return field.type in ('float', 'monetary')
    widget = (node.get('widget') or '').lower()
    if widget in ('monetary', 'float', 'float_time', 'monetary_field', 'percentage', 'percent'):
        return True
    field_name_lower = field_name.lower()
    if 'currency_id' in field_name_lower:
        return True
    return any(kw in field_name_lower for kw in NUMERIC_KEYWORDS)

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
            field = current_model._fields.get(field_name) if (current_model is not None and field_name) else None
            if _is_numeric_field(field, node, precision_key):
                _apply_precision(node, precision, precision_key)
            if field is not None and field.type in ('one2many', 'many2many'):
                try:
                    comodel = model.env[field.comodel_name]
                except KeyError:
                    comodel = None
                if comodel is not None:
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
