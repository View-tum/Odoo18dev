/** @odoo-module **/

import { registry } from "@web/core/registry";
import { radioField, RadioField } from "@web/views/fields/radio/radio_field";

export class MobileAdvancePaymentMethodRadio extends RadioField {
    get items() {
        const items = super.items || [];
        if (!this.props.record.data.is_mobile_warehouse) {
            return items;
        }
        return items.filter((item) => item[0] === "delivered");
    }
}

export const mobileAdvancePaymentMethodRadio = {
    ...radioField,
    component: MobileAdvancePaymentMethodRadio,
};

registry.category("fields").add("mobile_advance_payment_method", mobileAdvancePaymentMethodRadio);
