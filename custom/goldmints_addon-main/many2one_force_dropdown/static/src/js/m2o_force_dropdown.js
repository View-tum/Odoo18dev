/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { Many2OneField, many2OneField } from "@web/views/fields/many2one/many2one_field";

export class ForceDropdownMany2X extends Many2XAutocomplete {
    static template = "many2one_force_dropdown.ForceDropdownMany2X";

    shouldUseMobileDialog() {
        return false;  // only change: no mobile dialog
    }
}

export class M2OForceDropdownField extends Many2OneField {
    static components = {
        ...Many2OneField.components,
        Many2XAutocomplete: ForceDropdownMany2X,
    };
}

export const m2oForceDropdown = {
    ...many2OneField,
    component: M2OForceDropdownField,
};

registry.category("fields").add("m2o_force_dropdown", m2oForceDropdown);
