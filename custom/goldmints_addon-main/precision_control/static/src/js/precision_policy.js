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

const getModelFromWindow = () => {
    if (typeof window === "undefined") {
        return null;
    }
    const rawHash = window.location.hash || "";
    const hashParams = new URLSearchParams(rawHash.startsWith("#") ? rawHash.slice(1) : rawHash);
    return hashParams.get("model") || hashParams.get("res_model") || hashParams.get("active_model");
};

const getWindowPrecision = () => {
    const model = getModelFromWindow();
    const precisionFromModel = getPrecisionForModel(model);
    if (precisionFromModel !== null) {
        return precisionFromModel;
    }
    if (typeof window === "undefined") {
        return null;
    }
    const content = ((window.location.hash || "") + (window.location.pathname || "")).toLowerCase();
    if (content.includes("purchase")) return PRECISION_SETTINGS.purchase;
    if (content.includes("sale")) return PRECISION_SETTINGS.sale;
    if (content.includes("mrp")) return PRECISION_SETTINGS.mrp;
    if (content.includes("expense")) return PRECISION_SETTINGS.expense;
    if (content.includes("stock")) return PRECISION_SETTINGS.stock;
    if (content.includes("product")) return PRECISION_SETTINGS.product;
    if (content.includes("account") || content.includes("invoice") || content.includes("bill")) {
        return PRECISION_SETTINGS.account;
    }
    return null;
};

const getPolicyPrecision = (record, envModel = null, env = null, field = null) => {
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

    const precisionFromModel = getPrecisionForModel(model);
    if (precisionFromModel !== null) {
        return precisionFromModel;
    }

    const precisionFromWindow = getWindowPrecision();
    if (precisionFromWindow !== null) {
        return precisionFromWindow;
    }

    const fieldName = (field?.name || "").toLowerCase();
    if (
        field?.type === "monetary" ||
        fieldName.includes("amount") ||
        fieldName.includes("total") ||
        fieldName.includes("price") ||
        fieldName.includes("qty") ||
        fieldName.includes("quantity") ||
        fieldName.includes("quant")
    ) {
        return PRECISION_SETTINGS.account || 2;
    }

    return null;
};

const originalMonetaryExtractProps = monetaryField.extractProps;
monetaryField.extractProps = (params) => {
    const props = originalMonetaryExtractProps(params);
    props.precisionType = params.options.precision_type;
    return props;
};

const originalFloatExtractProps = floatField.extractProps;
floatField.extractProps = (params) => {
    const props = originalFloatExtractProps(params);
    props.precisionType = params.options.precision_type;
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
        let precision = null;
        if (this.props.precisionType) {
            precision = PRECISION_SETTINGS[this.props.precisionType];
        }
        if (precision === null) {
            precision = getPolicyPrecision(this.props.record, this.env.model?.resModel, this.env);
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
        let precision = null;
        if (this.props.precisionType) {
            precision = PRECISION_SETTINGS[this.props.precisionType];
        }
        if (precision === null) {
             precision = getPolicyPrecision(this.props.record, this.env.model?.resModel, this.env);
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
        let precision = null;
        if (this.props.precisionType) {
            precision = PRECISION_SETTINGS[this.props.precisionType];
        }
        if (precision === null) {
            precision = getPolicyPrecision(this.props.record, this.env.model?.resModel, this.env);
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
        const precision = getPolicyPrecision(this.props.record, this.env.model?.resModel, this.env);
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
    let precision = null;
    if (options.precisionType) {
        precision = PRECISION_SETTINGS[options.precisionType];
    }
    if (precision === null) {
        precision = getPolicyPrecision(options.record, options.model, null, options.field);
    }
    if (precision === null) {
        precision = getWindowPrecision();
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
    let precision = null;
    if (options.precisionType) {
        precision = PRECISION_SETTINGS[options.precisionType];
    }
    if (precision === null) {
        precision = getPolicyPrecision(options.record, options.model, null, options.field);
    }
    if (precision === null) {
        precision = getWindowPrecision();
    }
    if (precision === null) {
        const fieldName = (options.field?.name || "").toLowerCase();
        if (
            fieldName.includes("qty") ||
            fieldName.includes("quantity") ||
            fieldName.includes("quant") ||
            fieldName.includes("amount") ||
            fieldName.includes("total") ||
            fieldName.includes("price")
        ) {
            precision = PRECISION_SETTINGS.account || 2;
        }
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
        formatOptions.record = record;
        formatOptions.model = record.resModel || record.model?.resModel;
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
