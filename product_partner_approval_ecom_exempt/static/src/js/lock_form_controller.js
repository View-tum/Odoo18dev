/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";
import { onPatched } from "@odoo/owl";

patch(FormController.prototype, "product_partner_approval_ecom_exempt.lock_form", {
    setup() {
        this._super && this._super(...arguments);

        // Run after every render/patch
        onPatched(() => {
            const rec = this.model?.root;
            const isLocked = rec?.data?.is_lock;
            if (!isLocked || !this.el) return;

            // Disable all interactive controls in the form body
            this.el.querySelectorAll("input, textarea, select, button").forEach((el) => {
                // keep chatter controls enabled; skip statusbar buttons if you want
                if (el.closest(".o_Chatter_topbar, .o-mail-Composer, .o-mail-Thread")) return;
                el.setAttribute("disabled", "disabled");
                el.setAttribute("readonly", "readonly");
            });

            // Disable Edit button if present
            const editBtn = this.el.querySelector(".o_form_button_edit");
            if (editBtn) editBtn.setAttribute("disabled", "disabled");
        });
    },
});
