/* @odoo-module */
import { download } from "@web/core/network/download";
import { registry } from "@web/core/registry";

export function fileDownload(env, action) {
    download({
        data: action.params,
        url: "/web/content",
    });    
}

registry.category("actions").add("file_download", fileDownload);
