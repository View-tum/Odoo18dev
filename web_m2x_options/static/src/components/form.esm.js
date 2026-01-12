/** @odoo-module **/

import { registry } from "@web/core/registry";
import { exprToBoolean } from "@web/core/utils/strings";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { session } from "@web/session";
import { patch } from "@web/core/utils/patch";
import { isX2Many } from "@web/views/utils";

// Import fields
import { Many2OneField, many2OneField } from "@web/views/fields/many2one/many2one_field";
import { Many2ManyTagsField, many2ManyTagsField } from "@web/views/fields/many2many_tags/many2many_tags_field";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { FormController } from "@web/views/form/form_controller";

// Utility functions for props patching
function getBooleanOption(option, defaultValue = true) {
    return typeof option !== "undefined" ? evaluateBooleanExpr(option) : defaultValue;
}

function resolveCreateOption(props, attrs, options, ir_options) {
    if (options.create === false) props.canQuickCreate = false;
    else if (options.create) {
        props.canQuickCreate = getBooleanOption(attrs.can_create);
    } else if (!exprToBoolean(ir_options["web_m2x_options.create"])) {
        props.canQuickCreate = false;
    } else {
        props.canQuickCreate = getBooleanOption(attrs.can_create);
    }
}

function resolveCreateEditOption(props, attrs, options, ir_options) {
    if (options.create_edit === false) props.canCreateEdit = false;
    else if (options.create_edit) {
        props.canCreateEdit = getBooleanOption(attrs.can_create);
    } else if (!exprToBoolean(ir_options["web_m2x_options.create_edit"])) {
        props.canCreateEdit = false;
    } else {
        props.canCreateEdit = getBooleanOption(attrs.can_create);
    }
}

function resolveLimitOption(props, options, ir_options, isM2M = false) {
    const limit = Number(options.limit || ir_options["web_m2x_options.limit"] || 0);
    if (limit > 0) {
        props.searchLimit = isM2M ? limit - 1 : limit;
    }
}

function resolveOpenOption(props, options, ir_options) {
    if (options.open === true) props.canOpen = true;
    else if (options.open === false) props.canOpen = false;
    else props.canOpen = exprToBoolean(ir_options["web_m2x_options.open"]);
}

function applyCommonProps(props, attrs, options, isM2M = false) {
    const ir_options = session.web_m2x_options || {};
    resolveCreateOption(props, attrs, options, ir_options);
    resolveCreateEditOption(props, attrs, options, ir_options);
    resolveLimitOption(props, options, ir_options, isM2M);
    if (!isM2M) resolveOpenOption(props, options, ir_options);
    props.fieldColor = options.field_color;
    props.fieldColorOptions = options.colors;
    return props;
}

// Patch Many2OneField extractProps
patch(many2OneField, {
    extractProps({ attrs, context, decorations, options, string }, dynamicInfo) {
        const props = super.extractProps({ attrs, context, decorations, options, string }, dynamicInfo);
        return applyCommonProps(props, attrs, options, false);
    },
});

// Patch Many2XAutocomplete for fieldColor processing
patch(Many2XAutocomplete.prototype, {
    async loadOptionsSource(request) {
        const options = await super.loadOptionsSource(request);
        const { fieldColor, fieldColorOptions, resModel } = this.props;
        if (!fieldColor || !fieldColorOptions) return options;

        const value_ids = options.map(o => o.value);
        const records = await this.orm.call(resModel, "search_read", [], {
            domain: [["id", "in", value_ids]],
            fields: [fieldColor],
        });

        for (const record of records) {
            const option = options.find(o => o.value === record.id);
            if (option) option.style = `color: ${fieldColorOptions[record[fieldColor]] || "black"}`;
        }
        return options;
    },
});

// Patch Many2ManyTagsField extractProps
patch(many2ManyTagsField, {
    extractProps({ attrs, options, string }, dynamicInfo) {
        const props = super.extractProps({ attrs, options, string }, dynamicInfo);
        return applyCommonProps(props, attrs, options, true);
    },
});

// Patch FormController to limit x2many subview records
patch(FormController.prototype, {
    async _setSubViewLimit() {
        const ir_options = session.web_m2x_options || {};
        const limit = parseInt(ir_options["web_m2x_options.field_limit_entries"] || 0, 10);
        if (!limit) return;

        for (const fieldName in this.archInfo.fieldNodes) {
            const field = this.archInfo.fieldNodes[fieldName];
            if (!isX2Many(field) || field.invisible || !field.field.useSubView) continue;
            let viewType = field.viewMode?.replace("tree", "list") || "list,kanban";
            viewType = viewType.includes(",") ? (this.user ? "kanban" : "list") : viewType;
            field.viewMode = viewType;
            if (field.views?.[viewType]) field.views[viewType].limit = limit;
        }
    },

    setup() {
        super.setup(...arguments);
        this._setSubViewLimit();
    },
});

// Registry validation schema patch
patch(registry.category("fields").validationSchema, {
    m2oOptionsProps: { type: Function, optional: true },
    m2mOptionsProps: { type: Function, optional: true },
});
