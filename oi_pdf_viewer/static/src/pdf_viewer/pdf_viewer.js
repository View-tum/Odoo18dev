/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Layout } from "@web/search/layout";

export class PDFViewer extends Component {
    static template = "oi_pdf_viewer.PDFViewer";
    static components = {Layout};
    static props = {
        action: Object,
        actionId: { type: Number, optional: true },
        className: { type: String, optional: true },
        globalState: { type: Object, optional: true },
    };

    get display() {
        return {
            controlPanel: {},
        };
    }

    get iframeSource() {
        const {params, context} = this.props.action;
        const {report_name} = params;
        const type = params.type || 'pdf';                

        let url;
        if (report_name) {
            const docids = params.docids || context.active_ids;
            url = `/report/${type}/${report_name}/${docids}`
        }
        else {
            const model = params.model || 'ir.attachment';
            const field = params.field || 'raw';
            const id = params.id || context.active_id;
            url = `/web/content/${model}/${id}/${field}`
        }
        if (type == "pdf")
            url = "/web/static/lib/pdfjs/web/viewer.html?file=" + url;
        return url;
    }

}

registry.category("actions").add("action_pdf_viewer", PDFViewer);
