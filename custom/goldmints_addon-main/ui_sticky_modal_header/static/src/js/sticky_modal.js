/** @odoo-module **/

import { registry } from "@web/core/registry";

const stickyModalService = {
    start() {
        this._setupMutationObserver();
    },

    _setupMutationObserver() {
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === 1) {
                        if (node.classList?.contains('modal') || node.classList?.contains('o_dialog') || node.classList?.contains('o_select_create_popup')) {
                            this._handleNewDialog(node);
                        } else if (node.querySelector?.('.modal, .o_dialog, .o_select_create_popup')) {
                            node.querySelectorAll('.modal, .o_dialog, .o_select_create_popup').forEach(d => this._handleNewDialog(d));
                        }
                    }
                });
            });
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    },

    _handleNewDialog(dialog) {
        const interval = setInterval(() => {
            if (!dialog.isConnected) {
                clearInterval(interval);
                return;
            }
            this._applySticky(dialog);
        }, 1000); // 1 second is enough for production
    },

    _applySticky(dialog) {
        const theads = dialog.querySelectorAll('.o_list_table thead, .o_list_renderer table thead');
        if (theads.length === 0) return;

        theads.forEach(thead => {
            const modalBody = dialog.querySelector('.modal-body');
            if (!modalBody) return;

            modalBody.style.setProperty('overflow-y', 'auto', 'important');
            modalBody.style.setProperty('display', 'flex', 'important');
            modalBody.style.setProperty('flex-direction', 'column', 'important');

            let current = thead.parentElement;
            while (current && current !== modalBody) {
                if (current.tagName !== 'THEAD' && current.tagName !== 'TBODY') {
                    current.style.setProperty('overflow', 'visible', 'important');
                    current.style.setProperty('overflow-x', 'visible', 'important');
                    current.style.setProperty('overflow-y', 'visible', 'important');
                    current.style.setProperty('height', 'auto', 'important');
                }
                current = current.parentElement;
            }

            thead.style.setProperty('position', 'sticky', 'important');
            thead.style.setProperty('top', '0', 'important');
            thead.style.setProperty('z-index', '100', 'important');
            thead.style.setProperty('background-color', '#ffffff', 'important');

            thead.querySelectorAll('th').forEach(th => {
                th.style.setProperty('background-color', '#ffffff', 'important');
                th.style.setProperty('position', 'sticky', 'important');
                th.style.setProperty('top', '0', 'important');
                th.style.setProperty('z-index', '100', 'important');
            });
        });
    }
};

registry.category("services").add("sticky_modal_header", stickyModalService);
