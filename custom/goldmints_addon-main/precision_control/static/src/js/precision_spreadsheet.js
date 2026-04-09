/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListUIPlugin } from "@spreadsheet/list/plugins/list_ui_plugin";
import { OdooPivot } from "@spreadsheet/pivot/odoo_pivot";
import { helpers as spreadsheetHelpers } from "@odoo/o-spreadsheet";
import {
    applyDecimalsToCurrencyFormat,
    buildNumberFormat,
    getPrecisionForModel,
    loadPrecisionSettings,
} from "./precision_settings";

loadPrecisionSettings();

const isValidSpreadsheetFormat = (format, locale) => {
    if (!format || typeof format !== "string") return false;
    try {
        spreadsheetHelpers.formatValue(0, { format, locale });
        return true;
    } catch (e) {
        return false;
    }
};

const originalGetListFormat = ListUIPlugin.prototype._getListFormat;
patch(ListUIPlugin.prototype, {
    _getListFormat(listId, position, field) {
        try {
            const dataSource = this.getters.getListDataSource?.(listId);
            const model = dataSource?._metaData?.resModel;
            const precision = getPrecisionForModel(model);
            if (precision !== null && field?.type === "monetary") {
                const currency = this.getListCurrency?.(listId, position, field.currency_field);
                if (currency) {
                    return this.getters.computeFormatFromCurrency({
                        ...currency,
                        decimalPlaces: precision,
                    });
                }
                return buildNumberFormat(precision);
            }
            return originalGetListFormat.call(this, listId, position, field);
        } catch (e) {
            return originalGetListFormat.call(this, listId, position, field);
        }
    },
});

const originalGetPivotFieldFormat = OdooPivot.prototype._getPivotFieldFormat;
patch(OdooPivot.prototype, {
    _getPivotFieldFormat(fieldName, value) {
        let format;
        try {
            format = originalGetPivotFieldFormat.call(this, fieldName, value);
        } catch (e) {
            return undefined;
        }
        try {
            const precision = getPrecisionForModel(this.coreDefinition?.model);
            if (precision === null || !format) {
                return format;
            }
            const parsed = this.parseGroupField?.(fieldName);
            const locale = this.getters?.getLocale?.();
            if (parsed?.field?.type === "monetary") {
                const candidate =
                    applyDecimalsToCurrencyFormat(format, precision) || buildNumberFormat(precision);
                if (isValidSpreadsheetFormat(candidate, locale)) {
                    return candidate;
                }
                const fallback = buildNumberFormat(precision);
                return isValidSpreadsheetFormat(fallback, locale) ? fallback : format;
            }
            if (parsed?.field?.type === "float") {
                const candidate = buildNumberFormat(precision);
                return isValidSpreadsheetFormat(candidate, locale) ? candidate : format;
            }
            return format;
        } catch (e) {
            return format;
        }
    },
});
