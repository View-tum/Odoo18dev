/** @odoo-module **/
import { registry } from "@web/core/registry";

const FIELD_NAMES = ["ref_seg1", "ref_seg2", "ref_seg3", "ref_seg4"];
const MAXLEN = { ref_seg1: 2, ref_seg2: 3, ref_seg3: 2, ref_seg4: 5 };
const FIELD_RULES = {
    ref_seg1: /^[A-Za-z]{0,2}$/,
    ref_seg2: /^[A-Za-z]{0,3}$/,
    ref_seg3: /^[A-Za-z]{0,2}$/,
    ref_seg4: /^\d+$/,
};
const INSERT_TYPES = new Set([
    "insertText",
    "insertFromPaste",
    "insertFromDrop",
    "insertReplacementText",
    "insertCompositionText",
]);

function findInputs(root) {
    return FIELD_NAMES.map((name) => {
        const wrapper = root.querySelector(`[name="${name}"]`);
        const inp = wrapper && wrapper.querySelector("input, textarea");
        return inp || null;
    });
}

function attachHandlers(inputs) {
    inputs.forEach((inp, idx) => {
        if (!inp || inp.dataset.pcnBound === "1") return;
        inp.dataset.pcnBound = "1";
        inp.tabIndex = 200 + idx;

        const fieldName = FIELD_NAMES[idx];
        const onInput = () => {
            const hardMax = parseInt(inp.getAttribute("maxlength") || "0", 10) || MAXLEN[fieldName];
            if (hardMax > 0 && inp.value.length >= hardMax) {
                const next = inputs[idx + 1];
                if (next && !next.disabled) next.focus();
            }
        };

        const onKeydown = (ev) => {
            if (ev.key === "Backspace") {
                const atStart = inp.selectionStart === 0 && inp.selectionEnd === 0;
                if ((inp.value.length === 0 || atStart) && idx > 0) {
                    const prev = inputs[idx - 1];
                    if (prev && !prev.disabled) {
                        ev.preventDefault();
                        prev.focus();
                        const len = prev.value.length;
                        prev.setSelectionRange(len, len);
                    }
                }
            }
        };

        const onBeforeInput = (ev) => {
            const rule = FIELD_RULES[fieldName];
            if (!rule || !INSERT_TYPES.has(ev.inputType)) return;
            const data = ev.data ?? "";
            if (!data) return;
            const start = inp.selectionStart ?? inp.value.length;
            const end = inp.selectionEnd ?? start;
            const candidate = inp.value.slice(0, start) + data + inp.value.slice(end);
            if (!rule.test(candidate)) {
                ev.preventDefault();
            }
        };

        const onInputSanitize = () => {
            const rule = FIELD_RULES[fieldName];
            if (!rule || rule.test(inp.value)) return;
            const cleaned =
                fieldName === "ref_seg4"
                    ? inp.value.replace(/\D+/g, "").slice(0, MAXLEN[fieldName])
                    : inp.value.replace(/[^A-Za-z]+/gi, "").slice(0, MAXLEN[fieldName]);
            inp.value = cleaned;
        };

        inp.addEventListener("beforeinput", onBeforeInput);
        inp.addEventListener("input", onInputSanitize);
        inp.addEventListener("input", onInput);
        inp.addEventListener("keydown", onKeydown);
    });
}

function setup(root) {
    const inputs = findInputs(root);
    if (inputs.every((i) => !i)) return;
    attachHandlers(inputs);
}

const AutoFocusService = {
    start() {
        const obs = new MutationObserver((mutations) => {
            for (const m of mutations) {
                for (const node of m.addedNodes) {
                    if (!(node instanceof HTMLElement)) continue;
                    const form = node.matches?.('.o_form_view') ? node : node.querySelector?.('.o_form_view');
                    if (!form) continue;
                    const isProductForm =
                        form.querySelector('form[dataset-model="product.template"]') ||
                        form.querySelector('[name="ref_seg1"]');
                    if (isProductForm) setup(form);
                }
            }
        });
        obs.observe(document.body, { childList: true, subtree: true });

        const prime = () => {
            const existing = document.querySelector('.o_form_view');
            if (existing) setup(existing);
        };
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", prime, { once: true });
        } else {
            prime();
        }
    },
};

registry.category("services").add("pcn_auto_focus_bootstrap", AutoFocusService);
