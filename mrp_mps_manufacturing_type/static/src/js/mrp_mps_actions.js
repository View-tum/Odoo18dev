/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { WithSearch } from "@web/search/with_search/with_search";
import { MainComponent } from "@mrp_mps/components/main";
import { MrpMpsSearchModel } from "@mrp_mps/search/mrp_mps_search_model";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { Component, onWillStart, onMounted, onWillUpdateProps } from "@odoo/owl";

export class MainComponentActionByType extends Component {
    static template = "mrp_mps.mrp_mps_action";
    static components = { WithSearch, MainComponent };
    static props = { ...standardActionServiceProps };

    setup() {
        this.viewService = useService("view");
        this.resModel = "mrp.production.schedule";

        const updateTitle = (ctx) => {
            if (!ctx) {
                return;
            }
            let newTitle = null;
            if (ctx.manufacturing_type === "plastic") {
                newTitle = "Plastic MPS";
            } else if (ctx.manufacturing_type === "pharma") {
                newTitle = "Pharma MPS";
            }

            if (!newTitle) {
                return; // default MPS or other usage → leave title as is
            }

            // Try to update the control panel / breadcrumb title
            // Odoo 17/18 usually uses .o_breadcrumb .active for the main title
            const selectors = [
                ".o_control_panel .breadcrumb-item.active",
                ".o_breadcrumb .active",
            ];

            for (const selector of selectors) {
                const el = document.querySelector(selector);
                if (el) {
                    el.textContent = newTitle;
                    break;
                }
            }
        };

        onWillStart(async () => {
            const ctx = this.props.action.context || {};

            const views = await this.viewService.loadViews({
                resModel: this.resModel,
                context: ctx,
                views: [[false, "search"]],
            });

            const baseDomain = [];
            if (ctx.manufacturing_type) {
                baseDomain.push(["manufacturing_type", "=", ctx.manufacturing_type]);
            }

            this.withSearchProps = {
                resModel: this.resModel,
                SearchModel: MrpMpsSearchModel,
                context: ctx,
                domain: baseDomain,
                orderBy: [{ name: "id", asc: true }],
                searchMenuTypes: ["filter", "favorite"],
                searchViewArch: views.views.search.arch,
                searchViewId: views.views.search.id,
                searchViewFields: views.fields,
                loadIrFilters: true,
            };
        });

        // After first render, change the title
        onMounted(() => {
            const ctx = this.props.action.context || {};
            updateTitle(ctx);
        });

        // If action changes (rare but possible), update again
        onWillUpdateProps((nextProps) => {
            const ctx = (nextProps.action && nextProps.action.context) || {};
            updateTitle(ctx);
        });
    }
}

registry
    .category("actions")
    .add("mrp_mps_client_action_by_type", MainComponentActionByType);
