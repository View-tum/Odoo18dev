/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import MpsLineComponent from "@mrp_mps/components/line";

const machinesPatch = {
    async _onClickOpenMachines() {
        if (!this.productionSchedule?.id) {
            return;
        }
        const action = await this.orm.call(
            "mrp.production.schedule",
            "action_open_mpc_machines_wizard",
            [this.productionSchedule.id]
        );
        if (!action) {
            return;
        }
        await this.actionService.doAction(action, {
            onClose: () => this.model.reload(this.productionSchedule.id),
        });
    },
};

patch(MpsLineComponent.prototype, machinesPatch);
