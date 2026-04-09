/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { registry } from "@web/core/registry";
import { utils as uiUtils } from "@web/core/ui/ui_service";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";

/**
 * Force many2one autocomplete to behave like desktop everywhere
 * (no mobile/tablet dialog, always inline dropdown).
 */

const alwaysInline = () => false;

const patchUiService = (uiService) => {
    if (!uiService || uiService.__m2oForceDesktopPatched) {
        return;
    }
    uiService.__m2oForceDesktopPatched = true;
    const originalStart = uiService.start.bind(uiService);
    uiService.start = (env, deps) => {
        const setDesktop = (ui) => {
            if (!ui) {
                return ui;
            }
            ui.isSmall = false;
            ui.size = 99; // force max size bucket
            ui.bus?.trigger?.("resize");
            return ui;
        };
        const ui = originalStart(env, deps);
        return ui?.then ? ui.then(setDesktop) : setDesktop(ui);
    };
};

const ensureUiServicePatched = () => {
    const servicesRegistry = registry.category("services");
    const uiService = servicesRegistry.get("ui", null);
    patchUiService(uiService);

    servicesRegistry.addEventListener("UPDATE", (ev) => {
        const { operation, key, value } = ev.detail || {};
        if (operation === "add" && key === "ui") {
            patchUiService(value);
        }
    });
};

const forceUiDesktop = () => {
    // 1) Kill the "small" flag at the UI service level so env.isSmall is always false.
    uiUtils.isSmall = () => false;

    // 2) Patch the ui service start so any new env starts in desktop mode.
    ensureUiServicePatched();

    // 3) If the UI service is already running (typical case), flip its state now.
    const activateDebugUi = () => {
        const ui = window.odoo?.__WOWL_DEBUG__?.root?.env?.services?.ui;
        if (ui) {
            ui.isSmall = false;
            ui.size = 99;
            ui.bus?.trigger?.("resize");
        } else {
            setTimeout(activateDebugUi, 200);
        }
    };
    activateDebugUi();
};

const forceMany2OneDropdown = () => {
    // Patch instance + static with the official patch helper (new signature)
    patch(Many2XAutocomplete.prototype, {
        shouldUseMobileDialog() {
            return alwaysInline();
        },
    });

    patch(Many2XAutocomplete, {
        shouldUseMobileDialog() {
            return alwaysInline();
        },
    });

    // Belt and suspenders: direct assign as well (in case caller bypasses patched prototype)
    Many2XAutocomplete.prototype.shouldUseMobileDialog = alwaysInline;
    Many2XAutocomplete.shouldUseMobileDialog = alwaysInline;
};

const run = () => {
    // Prevent multiple executions if loaded in several asset bundles
    if (window.__m2oForceDropdownPatched) {
        return;
    }
    window.__m2oForceDropdownPatched = true;

    console.warn("[many2one_force_dropdown] JS loaded (forcing inline dropdown, env.isSmall=false).");

    // Ensure the patch runs even if module ordering changes
    try {
        forceUiDesktop();
        forceMany2OneDropdown();
        console.warn("[many2one_force_dropdown] Forced desktop dropdown mode everywhere (env.isSmall=false).");
    } catch (err) {
        console.error("[many2one_force_dropdown] initial patch failed, retrying after delay", err);
        setTimeout(() => {
            try {
                forceUiDesktop();
                forceMany2OneDropdown();
                console.warn("[many2one_force_dropdown] Patch applied after retry.");
            } catch (err2) {
                console.error("[many2one_force_dropdown] patch retry failed", err2);
            }
        }, 500);
    }
};

run();
