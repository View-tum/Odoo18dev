/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";

patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);
        this._mpcDropdownHandler = this._mpcDropdownHandler || this._onMPCMoreDropdownClick.bind(this);
    },

    async start() {
        const res = await super.start(...arguments);
        if (this.el && this._mpcDropdownHandler) {
            this.el.addEventListener("click", this._mpcDropdownHandler);
        }
        return res;
    },

    willUnmount() {
        if (this.el && this._mpcDropdownHandler) {
            this.el.removeEventListener("click", this._mpcDropdownHandler);
        }
        return super.willUnmount(...arguments);
    },

    async _onMPCMoreDropdownClick(ev) {
        const link = ev.target.closest(".mrp-more-dropdown a[data-name]");
        if (!link) {
            return;
        }
        ev.preventDefault();
        ev.stopPropagation();

        const actionName = link.dataset.name;
        const actionType = link.dataset.type;
        if (actionType !== "action" || !actionName || this.modelName !== "mrp.production") {
            return;
        }

        const record = this.model.get?.(this.handle);
        const recordId = record?.resId || record?.data?.id;
        if (!recordId) {
            return;
        }
        const ctx = this.model.get?.(this.handle, { raw: true })?.context || {};

        const result = await this.orm.call(
            "mrp.production",
            actionName,
            [[recordId]],
            { context: ctx }
        );
        if (result && result.type) {
            await this.actionService.doAction(result);
        }
    },
});
