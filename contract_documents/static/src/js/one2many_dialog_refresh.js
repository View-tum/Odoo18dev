odoo.define('contract_documents.one2many_dialog_refresh', function (require) {
    "use strict";

    var Dialog = require('web.Dialog');
    var core = require('web.core');
    var rpc = require('web.rpc');

    // Patch Dialog.close to trigger an event on parent when closing a one2many form dialog
    Dialog.include({
        close: function () {
            var self = this;
            // call original
            var res = this._super.apply(this, arguments);
            try {
                // if dialog had a dataset and a parent, trigger a reload on the parent
                if (this && this.target && this.target.name === 'action' && this.dataset) {
                    // send an event on the bus to notify views to reload
                    core.bus.trigger('contract_documents:dialog_closed', {dataset: this.dataset});
                }
            } catch (e) {
                console.error('contract_documents: dialog refresh hook error', e);
            }
            return res;
        },
    });

    // Listener that will reload the parent one2many and chatter when dialog_closed is received
    var FormView = require('web.FormView');
    FormView.include({
        start: function () {
            var res = this._super.apply(this, arguments);
            core.bus.on('contract_documents:dialog_closed', this, function (payload) {
                try {
                    // reload the view to refresh one2many and chatter
                    if (this && this.controller) {
                        this.controller.reload();
                    }
                } catch (e) {
                    console.error('contract_documents: failed to reload form view after dialog close', e);
                }
            });
            return res;
        },
    });

});
