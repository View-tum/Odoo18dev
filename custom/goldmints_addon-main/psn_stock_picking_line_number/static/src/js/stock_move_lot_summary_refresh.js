/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { StockMoveX2ManyField } from "@stock/views/picking_form/stock_move_one2many";

patch(StockMoveX2ManyField.prototype, {
    setup() {
        super.setup(...arguments);
        const originalOpenRecord = this._openRecord?.bind(this);

        this._openRecord = (params = {}) => {
            const activeElement = document.activeElement;
            const onClose = params.onClose;
            const openedRecord = params.record;
            const result = originalOpenRecord({
                ...params,
                onClose: async () => {
                    const parentRecord = openedRecord?._parentRecord || this.props.record;
                    const recordDirty =
                        openedRecord && typeof openedRecord.isDirty === "function"
                            ? await openedRecord.isDirty()
                            : false;
                    const parentDirty =
                        parentRecord && typeof parentRecord.isDirty === "function"
                            ? await parentRecord.isDirty()
                            : false;

                    if (recordDirty || parentDirty) {
                        await parentRecord.save({ reload: true });
                    }
                    if (activeElement) {
                        activeElement.focus();
                    }
                    if (typeof onClose === "function") {
                        await onClose();
                    }
                },
            });
            return result;
        };
    },
});
