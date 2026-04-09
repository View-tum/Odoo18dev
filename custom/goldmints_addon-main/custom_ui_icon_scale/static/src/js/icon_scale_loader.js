/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

const iconScaleService = {
    async start() {
        try {
            const [scale, spacing] = await Promise.all([
                rpc("/web/dataset/call_kw/ir.config_parameter/get_param", {
                    model: "ir.config_parameter",
                    method: "get_param",
                    args: ["custom_ui_icon_scale.scale", "1.0"],
                    kwargs: {},
                }),
                rpc("/web/dataset/call_kw/ir.config_parameter/get_param", {
                    model: "ir.config_parameter",
                    method: "get_param",
                    args: ["custom_ui_icon_scale.spacing", "0.0"],
                    kwargs: {},
                })
            ]);
            document.documentElement.style.setProperty('--odoo-custom-icon-scale', scale || "1.0");
            document.documentElement.style.setProperty('--odoo-custom-icon-spacing', (spacing || "0") + "px");
        } catch (e) {
            console.error("Failed to load icon scale/spacing", e);
        }
    },
};

registry.category("services").add("iconScale", iconScaleService);
