/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListArchParser } from "@web/views/list/list_arch_parser";

const shopfloorVisibilityActions = new Set(["action_hide_from_shopfloor", "action_show_on_shopfloor"]);

patch(ListArchParser.prototype, {
    parse(xmlDoc, models, modelName) {
        const result = super.parse(xmlDoc, models, modelName);
        for (const column of result.columns) {
            if (column.type !== "button_group") {
                continue;
            }
            const hasShopfloorVisibilityAction = column.buttons.some((button) =>
                shopfloorVisibilityActions.has(button.clickParams.name)
            );
            if (hasShopfloorVisibilityAction) {
                column.buttonGroupLabel = "Show in Shopfloor";
            }
        }
        return result;
    },
});
