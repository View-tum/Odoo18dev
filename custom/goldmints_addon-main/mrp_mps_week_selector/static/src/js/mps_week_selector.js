/** @odoo-module **/

import { MainComponent } from "@mrp_mps/components/main";
import { MasterProductionScheduleModel } from "@mrp_mps/models/master_production_schedule_model";
import { reactive } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";

patch(MasterProductionScheduleModel.prototype, {
    setup() {
        super.setup?.(...arguments);
        if (!this.selectedPeriods) {
            this.selectedPeriods = reactive(new Set());
        }
    },

    notify() {
        super.notify(...arguments);
    },

    async load(domain, offset, limit, scale) {
        if (!this.selectedPeriods) {
            this.selectedPeriods = reactive(new Set());
        }
        await super.load(domain, offset, limit, scale);
        const count = (this.data && this.data.dates && this.data.dates.length) || 0;
        this.selectedPeriods.clear();
        for (let i = 0; i < count; i++) {
            this.selectedPeriods.add(i);
        }
    },

    togglePeriod(index) {
        if (this.selectedPeriods.has(index)) {
            this.selectedPeriods.delete(index);
        } else {
            this.selectedPeriods.add(index);
        }
        this.trigger("update");
    },

    selectAllPeriods() {
        const count = (this.data && this.data.dates && this.data.dates.length) || 0;
        for (let i = 0; i < count; i++) {
            this.selectedPeriods.add(i);
        }
        this.trigger("update");
    },

    unselectAllPeriods() {
        this.selectedPeriods.clear();
        this.trigger("update");
    },

    toggleAllPeriods() {
        const count = (this.data && this.data.dates && this.data.dates.length) || 0;
        if (this.selectedPeriods.size === count) {
            this.unselectAllPeriods();
        } else {
            this.selectAllPeriods();
        }
    },

    replenishAll() {
        const selectedIndices = Array.from(this.selectedPeriods);
        if (!selectedIndices.length) {
            return;
        }
        this.orm.search("mrp.production.schedule", this.domain).then((ids) => {
            this._actionReplenishWithPeriods(ids, true, selectedIndices);
        });
    },

    replenishSelectedRecords() {
        const selectedIndices = Array.from(this.selectedPeriods);
        if (!selectedIndices.length) {
            return;
        }
        this._actionReplenishWithPeriods(
            Array.from(this.selectedRecords),
            false,
            selectedIndices
        );
    },

    _actionReplenishWithPeriods(productionScheduleIds, basedOnLeadTime, selectedIndices) {
        this.mutex.exec(() => {
            return this.orm.call(
                "mrp.production.schedule",
                "action_replenish",
                [productionScheduleIds, basedOnLeadTime],
                {
                    context: {
                        mps_selected_period_indices: selectedIndices,
                    },
                }
            ).then(() => {
                if (productionScheduleIds.length === 1) {
                    this.reload(productionScheduleIds[0]);
                } else {
                    this.load();
                }
            });
        });
    },
});

patch(MainComponent.prototype, {
    get allPeriodsSelected() {
        const count =
            (this.model.data &&
                this.model.data.dates &&
                this.model.data.dates.length) ||
            0;
        return this.model.selectedPeriods.size === count && count > 0;
    },

    isPeriodSelected(index) {
        return this.model.selectedPeriods.has(index);
    },

    togglePeriodSelection(index) {
        this.model.togglePeriod(index);
    },

    toggleAllPeriodSelection() {
        this.model.toggleAllPeriods();
    },
});
