/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";
import { session } from "@web/session";

let PRECISION_SETTINGS = {
    sale: 2,
    purchase: 3,
    mrp: 4,
    account: 2,
    expense: 2,
    stock: 2,
    product: 2,
};

let settingsLoaded = false;

const sessionPrecision = session?.precision_settings;
if (sessionPrecision) {
    PRECISION_SETTINGS = { ...PRECISION_SETTINGS, ...sessionPrecision };
    settingsLoaded = true;
}

async function loadPrecisionSettings() {
    if (settingsLoaded) return;
    try {
        const result = await rpc("/precision_control/get_settings", {});
        if (result) {
            PRECISION_SETTINGS = { ...PRECISION_SETTINGS, ...result };
            settingsLoaded = true;
        }
    } catch (e) {
        console.warn("Precision Control: Could not load settings");
    }
}

loadPrecisionSettings();

const getPrecisionKeyFromModel = (model) => {
    if (!model) return null;
    if (model.startsWith("sale.")) return "sale";
    if (model.startsWith("purchase_request.")) return "purchase";
    if (model.startsWith("purchase.")) return "purchase";
    if (model.startsWith("mrp.")) return "mrp";
    if (model.startsWith("stock.")) return "stock";
    if (model.startsWith("product.")) return "product";
    if (model.startsWith("account.")) return "account";
    if (model.startsWith("hr.expense")) return "expense";
    return null;
};

const getPrecisionForModel = (model) => {
    const key = getPrecisionKeyFromModel(model);
    if (!key) return null;
    const precision = PRECISION_SETTINGS[key];
    return precision === undefined ? null : precision;
};

const buildNumberFormat = (precision) => {
    if (precision === null || precision === undefined) return undefined;
    const decimals = Math.max(0, precision);
    if (!decimals) return "#,##0";
    return "#,##0." + "0".repeat(decimals);
};

const applyDecimalsToCurrencyFormat = (format, precision) => {
    if (typeof format !== "string" || precision === null || precision === undefined) return format;
    const decimals = Math.max(0, precision);
    const decimalPart = decimals ? "." + "0".repeat(decimals) : "";
    const updateSection = (section) => section.replace(/#,##0(?:\\.0+)?/, `#,##0${decimalPart}`);
    return format.split(";").map(updateSection).join(";");
};

export {
    PRECISION_SETTINGS,
    loadPrecisionSettings,
    getPrecisionKeyFromModel,
    getPrecisionForModel,
    buildNumberFormat,
    applyDecimalsToCurrencyFormat,
};
