/** @odoo-module **/

import { makeContext } from "@web/core/context";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { CharField } from "@web/views/fields/char/char_field";
import { DateTimeField } from "@web/views/fields/datetime/datetime_field";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { MonetaryField } from "@web/views/fields/monetary/monetary_field";
import { x2ManyField, X2ManyField } from "@web/views/fields/x2many/x2many_field";

export class MobileTwoDigitMonetaryField extends MonetaryField {
    get currencyDigits() {
        return [16, 2];
    }
}

export class MobileMixedPaymentRows extends X2ManyField {
    static template = "sale_auto_confirm_invoice.MobileMixedPaymentRows";
    static components = {
        CharField,
        DateTimeField,
        Many2OneField,
        MobileTwoDigitMonetaryField,
    };

    get paymentLines() {
        return this.list.records;
    }

    get defaultAmount() {
        return Math.max(this.props.record.data.mobile_balance || 0, 0);
    }

    async addPaymentLine(paymentType) {
        const context = makeContext([
            this.props.context,
            {
                default_payment_type: paymentType,
                default_amount: this.defaultAmount,
            },
        ]);
        await this.list.addNewRecord({
            context,
            mode: "edit",
            position: "bottom",
        });
    }

    async removePaymentLine(line) {
        await this.list.delete(line);
    }

    paymentLabel(line) {
        return {
            bank: _t("Bank"),
            cash: _t("Cash"),
            cheque: _t("Cheque"),
            rounding: _t("ปัดเศษ"),
        }[line.data.payment_type];
    }

    paymentIcon(line) {
        return {
            bank: "fa-university",
            cash: "fa-money",
            cheque: "fa-check-square-o",
            rounding: "fa-exchange",
        }[line.data.payment_type];
    }
}

export const mobileMixedPaymentRows = {
    ...x2ManyField,
    component: MobileMixedPaymentRows,
};

registry.category("fields").add("mobile_mixed_payment_rows", mobileMixedPaymentRows);
