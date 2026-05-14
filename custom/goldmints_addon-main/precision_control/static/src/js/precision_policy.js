/** @odoo-module **/

import { AccountPaymentField } from "@account/components/account_payment_field/account_payment_field";
import { TaxTotalsComponent } from "@account/components/tax_totals/tax_totals";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { FloatField, floatField } from "@web/views/fields/float/float_field";
import { formatFloat, formatMonetary } from "@web/views/fields/formatters";
import { MonetaryField, monetaryField } from "@web/views/fields/monetary/monetary_field";
import { ListRenderer } from "@web/views/list/list_renderer";
import {
    PRECISION_SETTINGS,
    getPrecisionKeyFromModel,
    getPrecisionForModel,
    loadPrecisionSettings,
} from "./precision_settings";

const getTotalsPrecision = (totals) => {
    if (totals && totals.currency_pd) {
        return Math.round(-Math.log10(totals.currency_pd));
    }
    return null;
};
loadPrecisionSettings();

const PRECISION_FIELD_NAMES = {
    mrp: new Set([
        "actual_qty",
        "batch_size",
        "blocked_time",
        "bom_qty",
        "byproduct_cost",
        "capacity",
        "component_cost",
        "console_qty",
        "cost",
        "cost_actual",
        "cost_estimated",
        "cost_share",
        "cost_variance",
        "costs_hour",
        "credit",
        "cycle_time",
        "debit",
        "default_capacity",
        "current_mo_duration_expected",
        "duration",
        "duration_actual",
        "duration_expected",
        "duration_hours",
        "duration_minutes",
        "duration_unit",
        "efficiency_variance",
        "employee_costs_hour",
        "employee_ratio",
        "employee_cost_total",
        "extra_cost",
        "forecast_availability",
        "forecast_qty",
        "forecast_target_qty",
        "good_qty",
        "hierarchy_duration_expected",
        "hourly_rate",
        "late_backorder_remaining_qty",
        "max_to_replenish_qty",
        "min_to_replenish_qty",
        "mold_cost",
        "mold_cost_hour",
        "mold_cost_total",
        "new_product_qty",
        "new_qty",
        "oee",
        "oee_target",
        "old_product_qty",
        "operation_cost",
        "original_qty",
        "planned_qty",
        "price_unit",
        "price_variance",
        "product_consumed_qty_uom",
        "product_expected_qty_uom",
        "product_qty",
        "product_qty_available",
        "product_uom_qty",
        "product_virtual_available",
        "produced_qty",
        "productive_time",
        "production_capacity",
        "progress",
        "qty",
        "qty_done",
        "qty_produced",
        "qty_producing",
        "qty_production",
        "qty_reported_from_previous_wo",
        "qty_remaining",
        "qty_to_produce",
        "rate_variance",
        "recorded_qty",
        "replenish_qty",
        "scrap_qty",
        "should_consume_qty",
        "subcontracting_cost",
        "time_cycle",
        "time_cycle_manual",
        "time_efficiency",
        "time_start",
        "time_stop",
        "total_cost",
        "total_cost_actual",
        "total_cost_estimated",
        "total_hours",
        "total_variance",
        "unit_component_cost",
        "unit_cost",
        "unit_cost_actual",
        "unit_cost_std",
        "unit_factor",
        "unit_operation_cost",
        "unit_subcontracting_cost",
        "units_per_hour",
        "upd_product_qty",
        "upd_time_cycle_manual",
        "usage_variance",
        "workcenter_load",
        "quantity",
        "quantity_done",
        "reserved_availability",
    ]),
    stock: new Set([
        "additional_landed_cost",
        "added_value",
        "amount_total",
        "availability",
        "available_quantity",
        "avg_cost",
        "base_weight",
        "carrier_price",
        "cost_share",
        "current_quantity_svl",
        "current_value_svl",
        "cycle_time",
        "delay",
        "final_cost",
        "forecast_availability",
        "former_cost",
        "free_qty",
        "height",
        "inventory_diff_quantity",
        "inventory_quantity",
        "inventory_quantity_auto_apply",
        "incoming_qty",
        "max_weight",
        "move_quantity",
        "new_quantity",
        "new_value",
        "new_value_by_qty",
        "outgoing_qty",
        "packaging_length",
        "price_unit",
        "product_packaging_qty",
        "product_packaging_quantity",
        "product_packaging_uom_qty",
        "product_qty_available",
        "product_qty",
        "product_max_qty",
        "product_min_qty",
        "product_uom_qty",
        "product_virtual_available",
        "qty_multiple",
        "qty_on_hand_show",
        "qty_to_order",
        "qty_available",
        "qty_done",
        "quantity_product_uom",
        "quantity",
        "quantity_done",
        "remaining_qty",
        "remaining_value",
        "reserved_availability",
        "reserved_quantity",
        "sale_price",
        "scrap_qty",
        "shipping_volume",
        "shipping_weight",
        "should_consume_qty",
        "standard_price",
        "total_value",
        "unit_cost",
        "unit_factor",
        "value",
        "virtual_available",
        "visibility_days",
        "volume",
        "weight",
        "weight_bulk",
        "width",
        "qty_forecast",
        "qty_on_hand",
        "qty_to_order_manual",
    ]),
    product: new Set([
        "avg_cost",
        "available_threshold",
        "base_price",
        "buy_item_qty",
        "cost_per_unit",
        "default_extra_price",
        "discount",
        "excess_qty",
        "extra_price",
        "final_allowed_price",
        "fixed_price",
        "forecasted_quantity",
        "free_qty",
        "free_item_qty",
        "gross_weight",
        "incoming_qty",
        "issued_qty",
        "list_price",
        "lst_price",
        "max_qty",
        "min_qty",
        "min_quantity",
        "mrp_product_qty",
        "net_weight",
        "net_movement_qty",
        "on_hand_qty",
        "outgoing_qty",
        "percent_price",
        "price",
        "price_discount",
        "price_extra",
        "price_markup",
        "price_max_margin",
        "price_min_margin",
        "price_round",
        "price_surcharge",
        "produced_qty",
        "purchased_product_qty",
        "qty",
        "quantity_svl",
        "quantity",
        "qty_available",
        "qty_from",
        "qty_to",
        "received_qty",
        "reordering_max_qty",
        "reordering_min_qty",
        "sales_count",
        "service_upsell_threshold",
        "shortage_qty",
        "standard_price",
        "total_excess_qty",
        "total_issued_qty",
        "total_net_movement_qty",
        "total_on_hand_qty",
        "total_produced_qty",
        "total_received_qty",
        "total_shortage_qty",
        "total_value",
        "transform_factor",
        "upcharge_percent",
        "value_svl",
        "virtual_available",
        "volume",
        "weight",
    ]),
};

const normalizePrecision = (precision) => {
    const value = Number(precision);
    return Number.isInteger(value) && value >= 0 ? value : null;
};

const getPrecisionByType = (precisionType) => {
    if (!precisionType) {
        return null;
    }
    return normalizePrecision(PRECISION_SETTINGS[precisionType]);
};

const getModelPrecisionForField = (model, fieldName) => {
    const precision = normalizePrecision(getPrecisionForModel(model));
    if (precision === null) {
        return null;
    }
    const precisionKey = getPrecisionKeyFromModel(model);
    const allowedFields = PRECISION_FIELD_NAMES[precisionKey];
    if (allowedFields && (!fieldName || !allowedFields.has(fieldName))) {
        return null;
    }
    return allowedFields ? precision : null;
};

const getPolicyPrecision = (
    record,
    envModel = null,
    env = null,
    field = null,
    fieldName = null,
    precisionType = null
) => {
    const explicitPrecision = getPrecisionByType(precisionType);
    if (explicitPrecision !== null) {
        return explicitPrecision;
    }

    let model = record?.resModel ||
                record?.model?.resModel ||
                record?.model?.name ||
                record?.model?.config?.resModel ||
                record?.model?.metaData?.resModel ||
                (field && field.resModel) ||
                envModel ||
                (env && env.model && env.model.resModel) ||
                (env && env.config && env.config.resModel) ||
                (env && env.searchModel && env.searchModel.resModel) ||
                (record && record.model && record.model.resModel) ||
                (record && record.resModel);

    if (!model && env && env.config) {
        model = env.config.resModel;
    }

    const resolvedFieldName = fieldName || field?.name || field?.fieldName || "";
    return getModelPrecisionForField(model, resolvedFieldName);
};

const originalMonetaryExtractProps = monetaryField.extractProps;
monetaryField.extractProps = (params) => {
    const props = originalMonetaryExtractProps(params);
    props.precisionType = params.options?.precision_type;
    return props;
};

const originalFloatExtractProps = floatField.extractProps;
floatField.extractProps = (params) => {
    const props = originalFloatExtractProps(params);
    props.precisionType = params.options?.precision_type;
    return props;
};

Object.assign(MonetaryField.props, {
    precisionType: { type: String, optional: true },
});
Object.assign(FloatField.props, {
    precisionType: { type: String, optional: true },
});

patch(MonetaryField.prototype, {
    get currencyDigits() {
        let precision = getPrecisionByType(this.props.precisionType);
        if (precision === null) {
            precision = getPolicyPrecision(
                this.props.record,
                this.env.model?.resModel,
                this.env,
                this.props.record?.fields?.[this.props.name],
                this.props.name
            );
        }
        if (precision === null) {
            const resModel = this.props.record?.resModel || this.env.model?.resModel;
            if (resModel && (resModel.startsWith('account.') || resModel === 'account.move' || resModel === 'account.move.line')) {
                precision = PRECISION_SETTINGS['account'] || 2;
            }
        }
        if (precision !== null) {
            return [16, precision];
        }
        return super.currencyDigits;
    },
    get formattedValue() {
        let precision = getPrecisionByType(this.props.precisionType);
        if (precision === null) {
             precision = getPolicyPrecision(
                this.props.record,
                this.env.model?.resModel,
                this.env,
                this.props.record?.fields?.[this.props.name],
                this.props.name
            );
        }
        if (precision !== null) {
            return formatMonetary(this.value, {
                currencyId: this.currencyId,
                currencyField: this.props.currencyField,
                digits: [16, precision],
                noSymbol: !this.props.readonly || this.props.hideSymbol,
            });
        }
        if (this.props.options && (this.props.options.digits || this.props.options.decimal_precision)) {
            const optPrecision = this.props.options.decimal_precision || this.props.options.digits?.[1];
            if (optPrecision !== undefined) {
                 return formatMonetary(this.value, {
                    currencyId: this.currencyId,
                    currencyField: this.props.currencyField,
                    digits: [16, optPrecision],
                    noSymbol: !this.props.readonly || this.props.hideSymbol,
                });
            }
        }
        return super.formattedValue;
    }
});

patch(FloatField.prototype, {
    get formattedValue() {
        let precision = getPrecisionByType(this.props.precisionType);
        if (precision === null) {
            precision = getPolicyPrecision(
                this.props.record,
                this.env.model?.resModel,
                this.env,
                this.props.record?.fields?.[this.props.name],
                this.props.name
            );
        }
        if (precision !== null) {
            return formatFloat(this.value, {
                digits: [16, precision],
                noSymbol: true,
            });
        }
        if (this.props.options && (this.props.options.digits || this.props.options.decimal_precision)) {
            const optPrecision = this.props.options.decimal_precision || this.props.options.digits?.[1];
             if (optPrecision !== undefined) {
                 return formatFloat(this.value, {
                    digits: [16, optPrecision],
                    noSymbol: true,
                });
            }
        }
        return super.formattedValue;
    }
});

if (TaxTotalsComponent) {
    const TaxGroupComponent = TaxTotalsComponent.components.TaxGroupComponent;
    patch(TaxTotalsComponent.prototype, {
        formatMonetary(value) {
            let precision = getTotalsPrecision(this.totals);
            if (precision === null) {
                precision = getPolicyPrecision(this.props.record, this.env.model?.resModel, this.env);
            }
            if (precision === null && this.env.model?.resModel?.startsWith('account.')) {
                precision = PRECISION_SETTINGS['account'] || 2;
            }
            if (precision !== null) {
                return formatMonetary(value, {
                    currencyId: this.totals.currency_id,
                    digits: [16, precision]
                });
            }
            return super.formatMonetary(value);
        }
    });

    if (TaxGroupComponent) {
        patch(TaxGroupComponent.prototype, {
            formatMonetary(value) {
                let precision = getTotalsPrecision(this.props.totals);
                if (precision === null) {
                    precision = getPolicyPrecision(this.props.record, this.env.model?.resModel, this.env);
                }
                if (precision !== null) {
                     return formatMonetary(value, {
                        currencyId: this.props.totals.currency_id,
                        digits: [16, precision]
                    });
                }
                return super.formatMonetary(value);
            }
        });
    }
}

patch(AccountPaymentField.prototype, {
    getInfo() {
        const res = super.getInfo();
        const precision = getPrecisionByType("account");
        if (precision !== null && res.lines) {
            for (const line of res.lines) {
                line.amount_formatted = formatMonetary(line.amount, {
                    currencyId: line.currency_id,
                    digits: [16, precision]
                });
            }
        }
        return res;
    }
});

const formatterRegistry = registry.category("formatters");
const originalMonetaryFormatter = formatterRegistry.get("monetary");
const patchedMonetaryFormatter = (value, options = {}) => {
    let precision = getPrecisionByType(options.precisionType || options.precision_type);
    if (precision === null) {
        precision = getPolicyPrecision(
            options.record,
            options.model,
            null,
            options.field,
            options.fieldName,
            options.precisionType || options.precision_type
        );
    }
    if (precision === null) {
        const optPrecision = Array.isArray(options.digits) ? options.digits[1] : undefined;
        if (optPrecision !== undefined) {
            precision = optPrecision;
        }
    }
    if (precision !== null) {
        options = { ...options, digits: [16, precision] };
    }
    return originalMonetaryFormatter(value, options);
};
Object.assign(patchedMonetaryFormatter, originalMonetaryFormatter);
formatterRegistry.add("monetary", patchedMonetaryFormatter, { force: true });

const originalFloatFormatter = formatterRegistry.get("float");
const patchedFloatFormatter = (value, options = {}) => {
    let precision = getPrecisionByType(options.precisionType || options.precision_type);
    if (precision === null) {
        precision = getPolicyPrecision(
            options.record,
            options.model,
            null,
            options.field,
            options.fieldName,
            options.precisionType || options.precision_type
        );
    }
    if (precision !== null) {
        options = { ...options, digits: [16, precision] };
    }
    return originalFloatFormatter(value, options);
};
Object.assign(patchedFloatFormatter, originalFloatFormatter);
formatterRegistry.add("float", patchedFloatFormatter, { force: true });

patch(ListRenderer.prototype, {
    getFormattedValue(column, record) {
        const fieldName = column.name;
        if (column.options?.enable_formatting === false) {
            const value = record.data[fieldName];
            return value === false ? "" : value;
        }
        const field = record.fields[fieldName];
        const formatter = registry.category("formatters").get(field.type, (val) => val);
        const formatOptions = {};
        if (formatter.extractOptions) {
            Object.assign(formatOptions, formatter.extractOptions(column));
        }
        formatOptions.data = record.data;
        formatOptions.field = field;
        formatOptions.fieldName = fieldName;
        formatOptions.record = record;
        formatOptions.model = record.resModel || record.model?.resModel;
        formatOptions.precisionType = column.options?.precision_type || column.options?.precisionType;
        return record.data[fieldName] !== undefined
            ? formatter(record.data[fieldName], formatOptions)
            : "";
    },
    get aggregates() {
        let values;
        if (this.props.list.selection && this.props.list.selection.length) {
            values = this.props.list.selection.map((record) => record.data);
        } else if (this.props.list.isGrouped) {
            values = this.props.list.groups.map((group) => group.aggregates);
        } else {
            values = this.props.list.records.map((record) => record.data);
        }

        const aggregates = {};
        const formatters = registry.category("formatters");
        const model = this.props.list.resModel;

        for (const column of this.allColumns) {
            if (column.type !== "field") {
                continue;
            }
            const fieldName = column.name;
            if (fieldName in this.optionalActiveFields && !this.optionalActiveFields[fieldName]) {
                continue;
            }
            const field = this.fields[fieldName];
            const fieldValues = values.map((value) => value[fieldName]).filter((value) => value || value === 0);
            if (!fieldValues.length) {
                continue;
            }
            const type = field.type;
            if (type !== "integer" && type !== "float" && type !== "monetary") {
                continue;
            }
            const { attrs, widget } = column;
            const aggregateFunc =
                (attrs.sum && "sum") ||
                (attrs.avg && "avg") ||
                (attrs.max && "max") ||
                (attrs.min && "min");

            let currencyId;
            if (type === "monetary" || widget === "monetary") {
                const currencyField =
                    column.options.currency_field ||
                    this.fields[fieldName].currency_field ||
                    "currency_id";
                if (!(currencyField in this.props.list.activeFields)) {
                    aggregates[fieldName] = {
                        help: _t("No currency provided"),
                        value: "-",
                    };
                    continue;
                }
                currencyId = values[0][currencyField] && values[0][currencyField][0];
                if (currencyId && aggregateFunc) {
                    const sameCurrency = values.every(
                        (value) => currencyId === value[currencyField][0]
                    );
                    if (!sameCurrency) {
                        aggregates[fieldName] = {
                            help: _t("Different currencies cannot be aggregated"),
                            value: "-",
                        };
                        continue;
                    }
                }
            }

            if (aggregateFunc) {
                let aggregateValue = 0;
                if (aggregateFunc === "max") {
                    aggregateValue = Math.max(-Infinity, ...fieldValues);
                } else if (aggregateFunc === "min") {
                    aggregateValue = Math.min(Infinity, ...fieldValues);
                } else if (aggregateFunc === "avg") {
                    aggregateValue = fieldValues.reduce((acc, val) => acc + val, 0) / fieldValues.length;
                } else if (aggregateFunc === "sum") {
                    aggregateValue = fieldValues.reduce((acc, val) => acc + val, 0);
                }

                const formatter = formatters.get(widget, false) || formatters.get(type, false);
                const formatOptions = {
                    digits: attrs.digits ? JSON.parse(attrs.digits) : undefined,
                    escape: true,
                    field,
                    model,
                };
                if (currencyId) {
                    formatOptions.currencyId = currencyId;
                }
                aggregates[fieldName] = {
                    help: attrs[aggregateFunc],
                    value: formatter ? formatter(aggregateValue, formatOptions) : aggregateValue,
                };
            }
        }
        return aggregates;
    },
    formatAggregateValue(group, column) {
        const { widget, attrs } = column;
        const field = this.props.list.fields[column.name];
        const aggregateValue = group.aggregates[column.name];
        if (!(column.name in group.aggregates)) {
            return "";
        }
        const formatters = registry.category("formatters");
        const formatter = formatters.get(widget, false) || formatters.get(field.type, false);
        const formatOptions = {
            digits: attrs.digits ? JSON.parse(attrs.digits) : field.digits,
            escape: true,
            field,
            model: this.props.list.resModel,
        };
        return formatter ? formatter(aggregateValue, formatOptions) : aggregateValue;
    },
});

const patchExpenseDashboardPrecision = () => {
    const viewRegistry = registry.category("views");
    const viewKeys = ["hr_expense_dashboard_tree", "hr_expense_dashboard_kanban"];
    let patchedAny = false;

    for (const key of viewKeys) {
        const view = viewRegistry.get(key, null);
        const dashboardComponent = view?.Renderer?.components?.ExpenseDashboard;
        if (!dashboardComponent || dashboardComponent.__precisionControlPatched) {
            continue;
        }

        patch(dashboardComponent.prototype, {
            renderMonetaryField(value, currency_id) {
                const precision = PRECISION_SETTINGS.expense ?? 2;
                return formatMonetary(value, {
                    currencyId: currency_id,
                    digits: [16, precision],
                });
            },
        });

        dashboardComponent.__precisionControlPatched = true;
        patchedAny = true;
    }

    return patchedAny;
};

if (!patchExpenseDashboardPrecision() && typeof window !== "undefined") {
    const startedAt = Date.now();
    const timer = window.setInterval(() => {
        if (patchExpenseDashboardPrecision() || Date.now() - startedAt > 10000) {
            window.clearInterval(timer);
        }
    }, 250);
}
