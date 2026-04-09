/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";

patch(Many2OneField.prototype, {
    get Many2XAutocompleteProps() {
        const props = super.Many2XAutocompleteProps;

        if (session.allow_quick_create === false) {
            props.quickCreate = null;
            props.activeActions = {
                ...props.activeActions,
                create: false,
                createEdit: false,
            };
        }

        return props;
    },
});
