/** @odoo-module **/

import { TaxTotalsComponent } from "@account/components/tax_totals/tax_totals";
import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";
import { formatMonetary } from "@web/views/fields/formatters";
import { MonetaryField } from "@web/views/fields/monetary/monetary_field";

let PRECISION_SETTINGS = {
    'sale': 2,
    'purchase': 3,
    'mrp': 4,
    'account': 2,
    'stock': 6,
    'product': 6,
};

let settingsLoaded = false;

async function loadPrecisionSettings() {
    if (settingsLoaded) return;
    try {
        const result = await rpc('/precision_control/get_settings', {});
        if (result) {
            PRECISION_SETTINGS = result;
            settingsLoaded = true;
        }
    } catch (e) {
        console.warn('Precision Control: Could not load settings, using defaults');
    }
}

loadPrecisionSettings();

const getPolicyPrecision = (record) => {
    if (!record) return null;
    const model = record.resModel || record.model?.resModel || record.model?.name;
    if (!model) return null;

    if (model.startsWith('sale.')) return PRECISION_SETTINGS['sale'];
    if (model.startsWith('purchase.')) return PRECISION_SETTINGS['purchase'];
    if (model.startsWith('mrp.')) return PRECISION_SETTINGS['mrp'];
    if (model.startsWith('account.')) return PRECISION_SETTINGS['account'];
    if (model.startsWith('stock.')) return PRECISION_SETTINGS['stock'];
    if (model.startsWith('product.')) return PRECISION_SETTINGS['product'];

    const context = record.context || {};
    const activeModel = context.active_model;
    if (activeModel) {
        if (activeModel.startsWith('sale.')) return PRECISION_SETTINGS['sale'];
        if (activeModel.startsWith('purchase.')) return PRECISION_SETTINGS['purchase'];
        if (activeModel.startsWith('mrp.')) return PRECISION_SETTINGS['mrp'];
        if (activeModel.startsWith('account.')) return PRECISION_SETTINGS['account'];
        if (activeModel.startsWith('stock.')) return PRECISION_SETTINGS['stock'];
        if (activeModel.startsWith('product.')) return PRECISION_SETTINGS['product'];
    }

    return null;
};

// ============================================================================
// MONETARY FIELD PATCH (For PR Totals and other Monetary fields)
// ============================================================================
patch(MonetaryField.prototype, {
    get currencyDigits() {
        const precision = getPolicyPrecision(this.props.record);
        if (precision !== null) {
            return [16, precision];
        }
        return super.currencyDigits;
    },
    get formattedValue() {
        const precision = getPolicyPrecision(this.props.record);
        if (precision !== null) {
            return formatMonetary(this.value, {
                currencyId: this.currencyId,
                currencyField: this.props.currencyField,
                digits: [16, precision],
                noSymbol: !this.props.readonly || this.props.hideSymbol,
            });
        }
        return super.formattedValue;
    }
});

// ============================================================================
// TAX TOTALS PATCH (Footer summary for SO/PO)
// ============================================================================
if (TaxTotalsComponent) {
    patch(TaxTotalsComponent.prototype, {
        formatMonetary(value) {
            const precision = getPolicyPrecision(this.props.record);
            if (precision !== null) {
                return formatMonetary(value, {
                    currencyId: this.totals.currency_id,
                    digits: [16, precision]
                });
            }
            return super.formatMonetary(value);
        }
    });
}
