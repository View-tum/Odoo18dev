/** @odoo-module **/

import { Component, onWillStart, onWillUpdateProps, useRef, useState } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useBus, useService } from "@web/core/utils/hooks";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { SearchModel } from "@web/search/search_model";
import { WithSearch } from "@web/search/with_search/with_search";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

const actionRegistry = registry.category("actions");

// -------------------------------------------------------------
// Root dashboard component (Parallel Shopfloor)
// -------------------------------------------------------------

export class ParallelShopfloorHome extends Component {
    setup() {
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.dialogService = useService("dialog");

        this.state = useState({
            loading: true,
            mos: [],
            allMos: [],  // Cache for client-side search
        });

        onWillStart(async () => {
            await this.loadMos();
        });

        onWillUpdateProps(async (nextProps) => {
            const oldDomain = JSON.stringify(this.props.searchDomain || []);
            const newDomain = JSON.stringify(nextProps.searchDomain || []);
            const oldContext = JSON.stringify(this.props.searchContext || {});
            const newContext = JSON.stringify(nextProps.searchContext || {});
            if (oldDomain !== newDomain || oldContext !== newContext) {
                // Use real domain object from next props, not the stringified value
                await this.loadMos(nextProps.searchDomain || []);
            }
        });
    }

    async loadMos(domain = this.props.searchDomain || []) {
        this.state.loading = true;
        const params = {};
        if (domain && domain.length) {
            params.domain = domain;
        }
        if (this.props.searchContext) {
            params.context = this.props.searchContext;
        }
        const res = await rpc("/mrp_parallel_console/get_mos", params);
        this.state.allMos = res.mos || [];
        this.state.mos = this.state.allMos;
        this.state.loading = false;
    }


    openConsole(mo) {
        // If product is tracked by lot/serial but MO has no lot yet,
        // open a simple wizard to assign LOT before entering console.
        if (mo.tracking !== "none" && !mo.has_lot) {
            this.actionService.doAction({
                type: "ir.actions.act_window",
                res_model: "mrp.parallel.assign.lot.wizard",
                view_mode: "form",
                views: [[false, "form"]],
                target: "new",
                context: {
                    default_production_id: mo.id,
                },
            });
            return;
        }

        this.actionService.doAction({
            type: "ir.actions.client",
            tag: "mrp_parallel_console.main_console",
            name: "Task Console",
            context: {
                default_production_id: mo.id,
                active_id: mo.id,
                active_model: "mrp.production",
            },
            params: {
                production_id: mo.id,
            },
        });
    }

    async confirmMo(mo) {
        this.dialogService.add(ConfirmationDialog, {
            body: `Confirm manufacturing order ${mo.name}?`,
            confirm: async () => {
                const res = await rpc("/mrp_parallel_console/confirm_mo", {
                    production_id: mo.id,
                });
                if (res && res.error) {
                    this.notification.add(res.error, { type: "danger" });
                    return;
                }
                await this.loadMos();
            },
            cancel: () => { },
        });
    }

    async closeMo(mo) {
        this.dialogService.add(ConfirmationDialog, {
            body: `Close manufacturing order ${mo.name}? This may trigger backorder dialogs.`,
            confirm: async () => {
                const res = await rpc("/mrp_parallel_console/manual_close_mo", {
                    production_id: mo.id,
                });
                if (res && res.error) {
                    this.notification.add(res.error, { type: "danger" });
                    return;
                }
                if (res && res.action && typeof res.action === "object") {
                    await this.actionService.doAction(res.action, {
                        onClose: () => this.loadMos(),
                    });
                } else {
                    await this.loadMos();
                }
            },
            cancel: () => { },
        });
    }

    stateBadgeClass(mo) {
        if (mo.state === "progress") {
            return "badge badge-success";
        } else if (mo.state === "confirmed") {
            return "badge badge-info";
        } else if (mo.state === "to_close") {
            return "badge badge-warning";
        }
        return "badge badge-secondary";
    }
}
ParallelShopfloorHome.template = "mrp_parallel_console.Home";
ParallelShopfloorHome.props = {
    ...standardActionServiceProps,
    searchDomain: { optional: true },
    searchContext: { optional: true },
    searchProps: { optional: true },
};
ParallelShopfloorHome.components = { SearchBar };

// -------------------------------------------------------------
// Root dashboard client action with WithSearch wrapper
// -------------------------------------------------------------

export class ParallelShopfloorHomeAction extends Component {
    setup() {
        this.viewService = useService("view");
        this.resModel = "mrp.production";

        onWillStart(async () => {
            const views = await this.viewService.loadViews(
                {
                    resModel: this.resModel,
                    context: this.props.action.context,
                    views: [[false, "search"]],
                },
                { load_filters: true }
            );
            const context = this.props.action.context || {};
            const domain = [];

            this.withSearchProps = {
                resModel: this.resModel,
                SearchModel,
                context,
                domain,
                orderBy: [{ name: "id", asc: false }],
                searchMenuTypes: ["filter", "favorite"],
                searchViewArch: views.views.search.arch,
                searchViewId: views.views.search.id,
                searchViewFields: views.fields,
                loadIrFilters: true,
            };
        });
    }
}
ParallelShopfloorHomeAction.template = "mrp_parallel_console.HomeAction";
ParallelShopfloorHomeAction.components = { WithSearch, ParallelShopfloorHome };
ParallelShopfloorHomeAction.props = { ...standardActionServiceProps };

// -------------------------------------------------------------
// Workorder console component
// -------------------------------------------------------------

export class ParallelWorkorderConsole extends Component {
    setup() {
        this.notification = useService("notification");
        this.actionService = useService("action");
        this.dialogService = useService("dialog");
        this.busService = useService("bus_service");
        this._productionId = null;
        this._lineUid = 0;
        this.scrapQtyRef = useRef("scrapQtyInput");

        this.state = useState({
            loading: true,
            workorders: [],
            selectedIds: new Set(),
            activeWo: null,
            drawerQtyInput: "",
            drawerQtyNote: "",
            drawerEmployeeToAdd: "",
            logEmployeeFilter: "",
            // Toggle for purple/grey important buttons on console toolbar
            canCloseProduction: false,
            moClosed: false,
            productionState: null,
            productionDisplay: "",
            employees: [],
            productionPrintMenu: [],
            productionPrintMenuLoaded: false,
            scrapModal: {
                open: false,
                workorder: null,
                products: [],
                locations: [],
                scrapLocations: [],
                productId: null,
                qty: 0,
                locationId: null,
                scrapLocationId: null,
                reason: "",
                lotName: "",
                lotId: null,
                availableLots: [],
                productType: "",
                workcenterDisplay: "",
            },
            pickingDrawer: {
                open: false,
                loading: false,
                saving: false,
                picking: null,
                availablePickings: [],
                activePickingId: null,
                printMenu: [],
                printMenuLoaded: false,
            },
        });

        useBus(this.busService, "notification", (notifications) => {
            notifications.forEach((notif) => {
                // Handle all workorder event types
                if (notif.type === "workorder_update" ||
                    notif.type === "workorder_started" ||
                    notif.type === "workorder_progress" ||
                    notif.type === "workorder_ready" ||
                    notif.type === "workorder_done" ||
                    notif.type === "workorder_cancel" ||
                    notif.type === "employees_assigned" ||
                    notif.type === "quantity_changed" ||
                    notif.type === "timer_toggled") {
                    this._handleWorkorderUpdate(notif.payload);
                }
            });
        });

        onWillStart(async () => {
            this._productionId = this._computeProductionId();
            if (this._productionId) {
                // Fix: Use dot separator to match backend channel format
                this.busService.addChannel(`mrp_parallel_console.production.${this._productionId}`);
            }
            await this.loadData(this._productionId);
            await this.loadEmployees();
            await this.ensureProductionPrintMenu();
        });
    }

    _getWorkorderStateLabel(state) {
        const labels = {
            ready: _t("Ready"),
            progress: _t("In Progress"),
            pending: _t("Waiting"),
            waiting: _t("Waiting"),
            done: _t("Done"),
            cancel: _t("Cancelled"),
        };
        return labels[state] || state;
    }

    _handleWorkorderUpdate(payload) {
        // Backend sends: { workorder_id, changes: {...}, timestamp, ... }
        const workorderId = payload.workorder_id || payload.id;
        if (!workorderId) return;

        const wo = this.state.workorders.find((w) => w.id === workorderId);
        if (!wo) return;

        // Extract changes from payload (backend Phase 3 sends delta updates)
        const changes = payload.changes || payload;

        // Update state if changed
        if (changes.state !== undefined) {
            wo.state = changes.state;
            if (changes.state_label !== undefined) {
                wo.state_label = changes.state_label;
            } else {
                wo.state_label = this._getWorkorderStateLabel(changes.state);
            }
        } else if (changes.state_label !== undefined) {
            wo.state_label = changes.state_label;
        }

        // Update dates
        if (changes.console_date_start !== undefined) {
            wo.console_date_start = changes.console_date_start;
        }
        if (changes.console_date_finished !== undefined) {
            wo.console_date_finished = changes.console_date_finished;
        }

        // Update employees (support both employee_ids and employee_names from backend)
        if (changes.employee_ids !== undefined) {
            const employeeIds = changes.employee_ids;
            const newEmployees = [];
            for (const empId of employeeIds) {
                const empObj = this.state.employees.find(e => e.id === empId);
                if (empObj) {
                    newEmployees.push(empObj);
                } else {
                    // Use employee_names from backend if available
                    const empName = changes.employee_names && changes.employee_names[employeeIds.indexOf(empId)]
                        ? changes.employee_names[employeeIds.indexOf(empId)]
                        : "Unknown";
                    newEmployees.push({ id: empId, name: empName });
                }
            }
            wo.employees = newEmployees;
        }

        // Update quantity if not currently being edited by user
        if (changes.console_qty !== undefined && !wo.isDirty) {
            wo.console_qty = changes.console_qty;
        }

        // Update timer status
        if (changes.timer_running !== undefined) {
            wo.console_timer_running = changes.timer_running;
        }

        // Sync active drawer if open
        if (this.state.activeWo && this.state.activeWo.id === workorderId) {
            if (changes.state !== undefined) {
                this.state.activeWo.state = changes.state;
                if (changes.state_label !== undefined) {
                    this.state.activeWo.state_label = changes.state_label;
                } else {
                    this.state.activeWo.state_label = this._getWorkorderStateLabel(changes.state);
                }
            } else if (changes.state_label !== undefined) {
                this.state.activeWo.state_label = changes.state_label;
            }
            if (changes.console_date_start !== undefined) {
                this.state.activeWo.console_date_start = changes.console_date_start;
            }
            if (changes.console_date_finished !== undefined) {
                this.state.activeWo.console_date_finished = changes.console_date_finished;
            }
            if (changes.employee_ids !== undefined) {
                const employeeIds = changes.employee_ids;
                const newEmployees = [];
                for (const empId of employeeIds) {
                    const empObj = this.state.employees.find(e => e.id === empId);
                    if (empObj) {
                        newEmployees.push(empObj);
                    } else {
                        const empName = changes.employee_names && changes.employee_names[employeeIds.indexOf(empId)]
                            ? changes.employee_names[employeeIds.indexOf(empId)]
                            : "Unknown";
                        newEmployees.push({ id: empId, name: empName });
                    }
                }
                this.state.activeWo.employees = newEmployees;
            }
            if (changes.console_qty !== undefined && !wo.isDirty) {
                this.state.activeWo.console_qty = changes.console_qty;
            }
            if (changes.timer_running !== undefined) {
                this.state.activeWo.console_timer_running = changes.timer_running;
            }
        }
    }

    _computeProductionId() {
        const action = this.props.action || {};
        const mergedContext = {
            ...(this.props.context || {}),
            ...(action.context || {}),
        };
        const params = action.params || {};
        return (
            mergedContext.default_production_id ||
            mergedContext.production_id ||
            mergedContext.active_id ||
            params.production_id ||
            params.id ||
            this.props.resId ||
            null
        );
    }

    async loadData(productionId = null, options = {}) {
        const { preserveSelection = false } = options || {};
        const previousSelection = preserveSelection
            ? new Set(this.state.selectedIds)
            : null;
        if (productionId) {
            this._productionId = productionId;
        } else if (!this._productionId) {
            this._productionId = this._computeProductionId();
        }
        this.state.loading = true;
        const res = await rpc("/mrp_parallel_console/get_data", {
            production_id: this._productionId,
        });
        const workorders = res.workorders || [];
        const firstWo = workorders.length ? workorders[0] : null;
        this.state.workorders = workorders;
        this.state.productionDisplay =
            res.production_display ||
            (firstWo ? firstWo.production_name : this.state.productionDisplay || "");
        if (Object.prototype.hasOwnProperty.call(res, "can_close_production")) {
            this.state.canCloseProduction = !!res.can_close_production;
        } else {
            this.state.canCloseProduction = false;
        }
        this.state.moClosed = !!res.mo_closed;
        this.state.productionState = res.production_state || null;
        if (previousSelection) {
            const retainedIds = this.state.workorders
                .filter((wo) => previousSelection.has(wo.id))
                .map((wo) => wo.id);
            this.state.selectedIds = new Set(retainedIds);
        } else {
            this.state.selectedIds = new Set();
        }
        this.state.loading = false;
    }

    async reloadWorkorders() {
        await this.loadData(this._productionId, { preserveSelection: true });
    }

    async loadEmployees() {
        const res = await rpc("/mrp_parallel_console/get_employees", {});
        this.state.employees = res || [];
    }

    async ensureProductionPrintMenu() {
        if (this.state.productionPrintMenuLoaded) {
            return;
        }
        try {
            const res = await rpc("/mrp_parallel_console/get_production_print_menu", {});
            this.state.productionPrintMenu = res.actions || [];
        } catch (error) {
            this.notification.add(
                error.message || "Unable to load print actions.",
                { type: "warning" }
            );
            this.state.productionPrintMenu = [];
        } finally {
            this.state.productionPrintMenuLoaded = true;
        }
    }

    get productionName() {
        const first = this.state.workorders[0];
        if (first && first.production_name) {
            return first.production_name;
        }
        return this.state.productionDisplay || "";
    }

    get productionId() {
        return this._productionId;
    }

    async _openDashboard() {
        try {
            await this.actionService.doAction(
                "mrp_parallel_console.mrp_parallel_console_action_root"
            );
        } catch (error) {
            this.notification.add(
                error?.message || "Failed to open shop floor dashboard.",
                { type: "warning" }
            );
        }
    }

    openProductionForm() {
        if (!this._productionId) {
            this.notification.add("No manufacturing order found.", {
                type: "warning",
            });
            return;
        }
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "mrp.production",
            res_id: this._productionId,
            view_mode: "form",
            views: [[false, "form"]],
        });
    }

    // ------------ selection ------------

    toggleSelect(wo) {
        if (this.state.selectedIds.has(wo.id)) {
            this.state.selectedIds.delete(wo.id);
        } else {
            this.state.selectedIds.add(wo.id);
        }
        this.state.selectedIds = new Set(this.state.selectedIds);
    }

    isSelected(wo) {
        return this.state.selectedIds.has(wo.id);
    }

    // ------------ selection helpers ------------
    isAllSelected() {
        return (
            this.state.workorders.length &&
            this.state.selectedIds.size === this.state.workorders.length
        );
    }

    toggleSelectAll() {
        if (this.isAllSelected()) {
            this.state.selectedIds = new Set();
        } else {
            const allIds = this.state.workorders.map((wo) => wo.id);
            this.state.selectedIds = new Set(allIds);
        }
    }

    async removeWorkorder(wo) {
        this.dialogService.add(ConfirmationDialog, {
            body: `Remove Station "${wo.workcenter_name}" from ${wo.name}?`,
            confirm: async () => {
                const res = await rpc("/mrp_parallel_console/delete_workorder", {
                    workorder_id: wo.id,
                });
                if (res && res.error) {
                    this.notification.add(res.error, { type: "danger" });
                    return;
                }
                if (res && res.message) {
                    this.notification.add(res.message, { type: "success" });
                }
                await this.loadData();
            },
            cancel: () => { },
        });
    }

    updateCardConsoleQty(wo, value) {
        wo.console_qty = value;
        wo.isDirty = true;
    }

    async saveCardConsoleQty(wo, value) {
        const qty = parseFloat(value ?? wo.console_qty ?? "0") || 0;
        wo.console_qty = qty;
        wo.isSaving = true;
        try {
            await rpc("/mrp_parallel_console/update_console", {
                lines: [
                    {
                        id: wo.id,
                        console_qty: qty,
                    },
                ],
            });
            wo.isDirty = false;
            // Optional: show a quick success flash or just rely on removing dirty state
        } catch (error) {
            this.notification.add(
                error.message || "Failed to update console quantity.",
                { type: "danger" }
            );
        } finally {
            wo.isSaving = false;
        }
    }

    onConsoleQtyKeydown(ev) {
        if (ev.key === "Enter") {
            ev.target.blur();
        }
    }

    _ensureSelectionOrWarn() {
        if (!this.state.selectedIds.size) {
            this.notification.add(
                "Please select at least one task.",
                { type: "warning" }
            );
            return false;
        }
        return true;
    }

    openEmployeesPicker() {
        if (this.state.moClosed) {
            this.notification.add(
                "This manufacturing order is already closed. Employees cannot be updated.",
                { type: "warning" }
            );
            return;
        }
        if (!this._ensureSelectionOrWarn()) {
            return;
        }
        const validWos = this.state.workorders.filter(
            (wo) => this.state.selectedIds.has(wo.id) && !wo.is_locked
        );
        if (!validWos.length) {
            this.notification.add(
                "Selected stations are locked (Busy/Maintenance).",
                { type: "danger" }
            );
            return;
        }
        const workorderIds = validWos.map((wo) => wo.id);
        this.dialogService.add(SelectCreateDialog, {
            title: "Search: Employees",
            resModel: "hr.employee",
            domain: [["active", "=", true]],
            multiSelect: true,
            context: { active_test: true },
            onSelected: async (employeeIds) => {
                const ids = employeeIds || [];
                if (!ids.length) {
                    this.dialogService.add(ConfirmationDialog, {
                        body: "Remove all employees from the selected tasks?",
                        confirm: async () => {
                            await this.assignEmployees(workorderIds, ids);
                        },
                        cancel: () => { },
                    });
                } else {
                    await this.assignEmployees(workorderIds, ids);
                }
            },
        });
    }

    createMaintenanceFromSelection() {
        const selected = Array.from(this.state.selectedIds || []);
        if (!selected.length) {
            this.notification.add(
                "Please select at least one task to create a report.",
                { type: "warning" }
            );
            return;
        }
        const wo = this.state.workorders.find((w) => w.id === selected[0]);
        if (!wo) {
            this.notification.add("Selected task not found.", { type: "danger" });
            return;
        }
        this.createMaintenance(wo);
    }

    async assignEmployees(workorderIds, employeeIds) {
        const res = await rpc("/mrp_parallel_console/assign_employees", {
            workorder_ids: workorderIds,
            employee_ids: employeeIds,
        });
        if (res && res.error) {
            this.notification.add(res.error, { type: "danger" });
            return;
        }

        const message =
            (res && res.message) ||
            (employeeIds && employeeIds.length
                ? "Employees assigned successfully. Click 'Start' button to begin work."
                : "Employees removed successfully.");

        // Note: Auto Start logic removed, relying on Manual Start
        this.notification.add(message, { type: "success" });

        await this.loadData();
    }

    // More dropdown wizard methods
    async openDeleteWorkCentersWizard() {
        if (!this.productionId) {
            this.notification.add("No production ID available", { type: "warning" });
            return;
        }

        await this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'mrp.work.center.delete.wizard',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'new',
            context: {
                active_id: this.productionId,
                active_model: 'mrp.production',
            },
        }, {
            onClose: () => {
                this.loadData();
            },
        });
    }

    async openAddWorkCentersWizard() {
        if (!this.productionId) {
            this.notification.add("No production ID available", { type: "warning" });
            return;
        }

        await this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'mrp.work.center.add.wizard',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'new',
            context: {
                active_id: this.productionId,
                active_model: 'mrp.production',
            },
        }, {
            onClose: () => {
                this.loadData();
            },
        });
    }

    async openAdjustPlannedQtyWizard() {
        if (!this.productionId) {
            this.notification.add("No production ID available", { type: "warning" });
            return;
        }

        await this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'mrp.work.center.adjust.qty.wizard',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'new',
            context: {
                active_id: this.productionId,
                active_model: 'mrp.production',
            },
        }, {
            onClose: () => {
                this.loadData();
            },
        });
    }

    async openQtyWizard() {
        if (!this._ensureSelectionOrWarn()) {
            return;
        }
        const ids = Array.from(this.state.selectedIds);
        await this.actionService.doAction(
            "mrp_parallel_console.action_parallel_console_qty_wizard",
            {
                additionalContext: {
                    default_workorder_ids: ids,
                },
                onClose: (result) => {
                    this._handleQtyWizardClose(result);
                    this.loadData();
                },
            }
        );
    }

    _handleQtyWizardClose(result) {
        const updates =
            result && result.context && result.context.mrp_parallel_console_updates;
        if (updates && updates.length) {
            const updatesById = {};
            for (const payload of updates) {
                updatesById[payload.id] = payload;
            }
            this.state.workorders = this.state.workorders.map((wo) => {
                const payload = updatesById[wo.id];
                if (!payload) {
                    return wo;
                }
                return {
                    ...wo,
                    console_qty: payload.console_qty,
                };
            });
            if (this.state.activeWo && updatesById[this.state.activeWo.id]) {
                Object.assign(this.state.activeWo, {
                    console_qty: updatesById[this.state.activeWo.id].console_qty,
                });
            }
        }
        this.loadData(null, { preserveSelection: true });
    }

    isRunning(wo) {
        return wo.state === 'progress';
    }

    // ------------ drawer ------------

    openDrawer(wo) {
        this.state.activeWo = JSON.parse(JSON.stringify(wo));
        if (!this.state.activeWo.qty_logs) {
            this.state.activeWo.qty_logs = [];
        }
        if (!this.state.activeWo.time_tracking) {
            this.state.activeWo.time_tracking = [];
        }
        this.state.drawerQtyInput = "";
        this.state.drawerQtyNote = "";
        this.state.drawerEmployeeToAdd = "";
        this.state.logEmployeeFilter = "";
    }

    closeDrawer() {
        this.state.activeWo = null;
        this.state.drawerQtyInput = "";
        this.state.drawerQtyNote = "";
        this.state.drawerEmployeeToAdd = "";
        this.state.logEmployeeFilter = "";
    }

    updateActiveField(field, value) {
        if (!this.state.activeWo) {
            return;
        }
        this.state.activeWo[field] = value;
    }

    get filteredQtyLogs() {
        if (!this.state.activeWo || !this.state.activeWo.qty_logs) {
            return [];
        }
        return this.state.activeWo.qty_logs;
    }

    toggleDrawerEmployee(empId, checked) {
        if (!this.state.activeWo) {
            return;
        }
        const current = this.state.activeWo.employees || [];
        const idx = current.findIndex((e) => e.id === empId);

        if (checked) {
            if (idx === -1) {
                const allEmps = this.state.employees || [];
                const emp =
                    allEmps.find((e) => e.id === empId) || { id: empId };
                current.push(emp);
            }
        } else {
            if (idx !== -1) {
                current.splice(idx, 1);
            }
        }

        this.state.activeWo.employees = [...current];
    }

    addDrawerEmployee() {
        if (!this.state.activeWo) {
            return;
        }

        // Open Odoo standard employee picker dialog
        this.dialogService.add(SelectCreateDialog, {
            title: "Search: Employees",
            resModel: "hr.employee",
            domain: [["active", "=", true]],
            multiSelect: true,
            context: { active_test: true },
            onSelected: async (employeeIds) => {
                const ids = employeeIds || [];
                if (!ids.length) {
                    // If no employees selected, clear all
                    this.state.activeWo.employees = [];
                } else {
                    // Map IDs to employee objects
                    const newEmployees = [];
                    for (const empId of ids) {
                        const empObj = this.state.employees.find(e => e.id === empId);
                        if (empObj) {
                            newEmployees.push(empObj);
                        } else {
                            // If employee not in loaded list, create minimal object
                            newEmployees.push({ id: empId, name: "Employee #" + empId });
                        }
                    }
                    this.state.activeWo.employees = newEmployees;
                }
            },
        });
    }

    clearDrawerEmployees() {
        if (!this.state.activeWo) {
            return;
        }
        this.state.activeWo.employees = [];
    }

    async addQtyLog() {
        if (!this.state.activeWo) {
            return;
        }
        const qty = parseFloat(this.state.drawerQtyInput || "0") || 0;
        if (qty <= 0) {
            this.notification.add("Please enter a quantity greater than zero.", { type: "warning" });
            return;
        }
        try {
            const res = await rpc("/mrp_parallel_console/add_qty_log", {
                workorder_id: this.state.activeWo.id,
                qty,
                note: this.state.drawerQtyNote || "",
                // Include currently assigned employees so they are recorded in the output log
                employee_ids: (this.state.activeWo.employees || []).map(e => e.id),
            });
            if (res && res.error) {
                this.notification.add(res.error, { type: "danger" });
                return;
            }
            const total = res.total ?? qty;
            this.state.activeWo.console_qty = total;
            this.state.activeWo.qty_logs = res.logs || [];
            this.state.drawerQtyInput = "";
            this.state.drawerQtyNote = "";
            this._syncCardQty(res.workorder_id, total, res.logs || []);
        } catch (error) {
            this.notification.add(
                error?.message || "Failed to add quantity log.",
                { type: "danger" }
            );
        }
    }

    _syncCardQty(workorderId, qty, logs) {
        const card = this.state.workorders.find((w) => w.id === workorderId);
        if (card) {
            card.console_qty = qty;
            if (logs) {
                card.qty_logs = logs;
            }
        }
    }

    async editQtyLog(log) {
        if (!log || !this.state.activeWo) {
            return;
        }
        const newQtyStr = window.prompt("Edit quantity", log.qty);
        if (newQtyStr === null) {
            return;
        }
        const qty = parseFloat(newQtyStr || "0");
        if (!qty || qty <= 0) {
            this.notification.add("Quantity must be greater than zero.", { type: "warning" });
            return;
        }
        const newNote = window.prompt("Edit note (optional)", log.note || "") ?? "";
        try {
            const res = await rpc("/mrp_parallel_console/update_qty_log", {
                log_id: log.id,
                qty,
                note: newNote,
            });
            if (res && res.error) {
                this.notification.add(res.error, { type: "danger" });
                return;
            }
            this.state.activeWo.console_qty = res.total ?? qty;
            this.state.activeWo.qty_logs = res.logs || [];
            this._syncCardQty(res.workorder_id, res.total ?? qty, res.logs || []);
        } catch (error) {
            this.notification.add(
                error?.message || "Failed to update quantity log.",
                { type: "danger" }
            );
        }
    }

    async openTimeTrackingPopup(log = null) {
        if (!this.state.activeWo) {
            return;
        }
        const log_date = log ? (log.log_date || log.create_date || null) : null;
        // Don't filter by start/end when opening Time Logs popup
        // console_date_start is reset on each Start, so filtering by it would exclude older logs
        const employee_ids = log && log.employees
            ? (log.employees || []).map((e) => e.id).filter((id) => !!id)
            : [];
        try {
            const res = await rpc("/mrp_parallel_console/get_time_tracking_action", {
                workorder_id: this.state.activeWo.id,
                log_date,
                employee_ids,
                // Removed start and end parameters to show all logs for the workorder
            });
            if (res && res.error) {
                this.notification.add(res.error, { type: "danger" });
                return;
            }
            if (res && res.action) {
                await this.actionService.doAction(res.action);
            }
        } catch (error) {
            this.notification.add(
                error?.message || "Unable to open time tracking.",
                { type: "danger" }
            );
        }
    }

    async saveActiveWo() {
        if (!this.state.activeWo) {
            return;
        }
        const wo = this.state.activeWo;
        const line = {
            id: wo.id,
            console_qty: parseFloat(wo.console_qty || "0") || 0,
            console_date_start: wo.console_date_start || false,
            console_date_finished: wo.console_date_finished || false,
            employee_ids: (wo.employees || []).map((e) => e.id),
        };
        await rpc("/mrp_parallel_console/update_console", { lines: [line] });
        this.notification.add("Work order updated.", { type: "success" });
        this.state.activeWo = null;
        await this.loadData();
    }

    // ------------ apply ------------

    async applyConsole() {
        let ids = Array.from(this.state.selectedIds);
        if (!ids.length) {
            this.dialogService.add(ConfirmationDialog, {
                body: "Close production for all workorders in this manufacturing order?",
                confirm: async () => {
                    ids = this.state.workorders.map((wo) => wo.id);
                    await this._executeApplyConsole(ids);
                },
                cancel: () => { },
            });
        } else {
            await this._executeApplyConsole(ids);
        }
    }

    async _executeApplyConsole(ids) {
        if (!ids.length) {
            this.notification.add("No work orders to close.", { type: "warning" });
            return;
        }

        const res = await rpc("/mrp_parallel_console/apply_console", {
            workorder_ids: ids,
        });
        if (res && res.status === "workorders_pending") {
            this.notification.add(
                res.error ||
                "Please mark every work center as Done before closing production.",
                { type: "warning" }
            );
            return;
        }
        if (res && res.error) {
            this.notification.add(res.error, { type: "danger" });
            return;
        }

        if (res && res.status === "quality_pending" && res.action) {
            await this.actionService.doAction(res.action, {
                onClose: () => {
                    this.loadData(null, { preserveSelection: true });
                },
            });
            return;
        }
        if (res && res.status === "lot_required" && res.action) {
            await this.actionService.doAction(res.action, {
                onClose: () => {
                    this.loadData(null, { preserveSelection: true });
                },
            });
            return;
        }

        if (res && res.scrap_skipped_count) {
            this.notification.add(
                `${res.scrap_skipped_count} scrap record(s) were not validated (insufficient stock / missing lot).`,
                { type: "warning" }
            );
        }

        const validAction =
            res &&
            res.action &&
            typeof res.action === "object" &&
            (res.action.type ||
                res.action.tag ||
                res.action.res_model ||
                res.action.views ||
                res.action.target);

        if (validAction) {
            await this.actionService.doAction(res.action, {
                onClose: async () => {
                    this.state.selectedIds = new Set();
                    await this._openDashboard();
                },
            });
        } else {
            this.notification.add("Production close request sent.", {
                type: "success",
            });
            this.state.selectedIds = new Set();
            await this._openDashboard();
        }

        // Note: Close logic handles picking validation if needed
    }


    async openPickingDrawer() {
        if (!this.productionId) {
            this.notification.add(
                "Please open a manufacturing order before picking components.",
                { type: "warning" }
            );
            return;
        }
        await this._openNextPickingAction();
    }

    async _openNextPickingAction(pickingId = null) {
        try {
            const params = { production_id: this.productionId };
            if (pickingId) {
                params.picking_id = pickingId;
            }
            const res = await rpc("/mrp_parallel_console/get_picking_action", params);
            if (res.error) {
                this.notification.add(res.error, { type: "danger" });
                return;
            }
            if (res.action) {
                const nextId = res.next_picking_id;
                await this.actionService.doAction(res.action, {
                    onClose: () => {
                        this._handlePickingActionClose(nextId);
                    },
                });
            } else {
                this.notification.add("No picking action found.", {
                    type: "warning",
                });
            }
        } catch (error) {
            this.notification.add(
                error.message || "Failed to open picking.",
                { type: "danger" }
            );
        }
    }

    async _handlePickingActionClose(nextPickingId) {
        if (nextPickingId) {
            this.dialogService.add(ConfirmationDialog, {
                body: "Another component picking is pending. Do you want to open it now?",
                confirm: async () => {
                    await this._openNextPickingAction(nextPickingId);
                },
                cancel: () => {
                    this.notification.add("Stopped automatic picking chain.", {
                        type: "info",
                    });
                },
            });
            return; // Wait for dialog
        }
        await this.loadData(null, { preserveSelection: true });
    }

    closePickingDrawer() {
        this.state.pickingDrawer.open = false;
        this.state.pickingDrawer.loading = false;
        this.state.pickingDrawer.saving = false;
        this.state.pickingDrawer.picking = null;
        this.state.pickingDrawer.availablePickings = [];
        this.state.pickingDrawer.activePickingId = null;
    }

    async printCurrentPicking(reportXmlId = null) {
        if (!this.productionId) {
            this.notification.add(
                "Please open a manufacturing order before printing.",
                { type: "warning" }
            );
            return;
        }
        if (!this.state.pickingDrawer.activePickingId) {
            this.notification.add(
                "No component picking available to print.",
                { type: "warning" }
            );
            return;
        }
        try {
            const pickingId = this.state.pickingDrawer.activePickingId;
            const res = await rpc("/mrp_parallel_console/get_picking_print_action", {
                picking_id: pickingId,
                report_xml_id: reportXmlId,
            });
            if (res.error) {
                this.notification.add(res.error, { type: "danger" });
                return;
            }
            if (res.action) {
                await this.actionService.doAction(res.action);
            } else {
                this.notification.add("No print action found.", {
                    type: "warning",
                });
            }
        } catch (error) {
            this.notification.add(
                error.message || "Failed to print picking.",
                { type: "danger" }
            );
        }
    }

    // ------------ Maintenance ------------
    async createMaintenance(wo) {
        const res = await rpc("/mrp_parallel_console/action_maintenance_request", {
            workorder_id: wo.id,
        });
        if (res && res.error) {
            this.notification.add(res.error, { type: "danger" });
            return;
        }
        if (res && res.action) {
            await this.actionService.doAction(res.action, {
                onClose: async () => {
                    await this.loadData(this._productionId, { preserveSelection: true });
                },
            });
        }
    }

    async printPickingReport(reportXmlId) {
        await this.printCurrentPicking(reportXmlId || null);
    }

    async printProductionAction(actionId, actionModel) {
        if (!this.productionId) {
            this.notification.add("Please open a manufacturing order before printing.", {
                type: "warning",
            });
            return;
        }
        try {
            const res = await rpc("/mrp_parallel_console/get_production_print_action", {
                production_id: this.productionId,
                action_id: actionId,
                action_model: actionModel,
            });
            if (res.error) {
                this.notification.add(res.error, { type: "danger" });
                return;
            }
            if (res.action) {
                await this.actionService.doAction(res.action);
            } else {
                this.notification.add("Print action executed.", { type: "success" });
            }
        } catch (error) {
            this.notification.add(
                error.message || "Failed to print manufacturing order.",
                { type: "danger" }
            );
        }
    }

    async _loadPickingData(pickingId = null) {
        try {
            await this.ensurePickingPrintMenu();
            const params = {
                production_id: this.productionId,
            };
            if (pickingId) {
                params.picking_id = pickingId;
            }
            const res = await rpc("/mrp_parallel_console/get_picking", params);
            if (res.error) {
                throw new Error(res.error);
            }
            this.state.pickingDrawer.picking = this._decoratePicking(res.picking);
            this.state.pickingDrawer.availablePickings =
                res.available_pickings || [];
            this.state.pickingDrawer.activePickingId = res.picking
                ? res.picking.id
                : null;
        } catch (error) {
            this.notification.add(
                error.message || "Unable to load component picking.",
                { type: "danger" }
            );
            this.state.pickingDrawer.open = false;
            this.state.pickingDrawer.availablePickings = [];
            this.state.pickingDrawer.activePickingId = null;
            this.state.pickingDrawer.picking = null;
        } finally {
            this.state.pickingDrawer.loading = false;
        }
    }

    async ensurePickingPrintMenu() {
        if (this.state.pickingDrawer.printMenuLoaded) {
            return;
        }
        try {
            const res = await rpc("/mrp_parallel_console/get_picking_print_menu", {});
            this.state.pickingDrawer.printMenu = res.reports || [];
        } catch (error) {
            this.notification.add(
                error.message || "Unable to load print reports.",
                { type: "warning" }
            );
            this.state.pickingDrawer.printMenu = [];
        } finally {
            this.state.pickingDrawer.printMenuLoaded = true;
        }
    }

    async switchPicking(ev) {
        const value = ev?.target?.value;
        const nextId = parseInt(value, 10);
        if (
            !value ||
            Number.isNaN(nextId) ||
            nextId === this.state.pickingDrawer.activePickingId
        ) {
            return;
        }
        this.state.pickingDrawer.loading = true;
        await this._loadPickingData(nextId);
    }

    async refreshPickingData() {
        if (!this.state.pickingDrawer.open) {
            return;
        }
        this.state.pickingDrawer.loading = true;
        const activeId = this.state.pickingDrawer.activePickingId || null;
        await this._loadPickingData(activeId);
    }

    _decoratePicking(picking) {
        if (!picking) {
            return null;
        }
        picking.moves = (picking.moves || []).map((move) => {
            const availableLots = move.available_lots || [];
            const hasAvailableLots = availableLots.length > 0;
            const hasBackendLines = move.move_lines && move.move_lines.length;
            const baseLines = hasAvailableLots
                ? this._buildAutoPickingLines(move, availableLots)
                : hasBackendLines
                    ? move.move_lines
                    : [this._defaultPickingLine(move)];

            move.move_lines = baseLines.map((line) => {
                const lineObj = {
                    id: line.id || null,
                    client_id: line.client_id || this._generateClientLineId(move),
                    lot_id: line.lot_id || null,
                    lot_name: line.lot_name || "",
                    qty_done: line.qty_done || 0,
                    location_id: line.location_id || null,
                };

                /*
                if (["lot", "serial"].includes(move.product_tracking) && !lineObj.lot_id && availableLots.length > 0) {
                    const autoLot = availableLots[0];

                    lineObj.lot_id = autoLot.id;
                    lineObj.lot_name = autoLot.name;

                    const currentReq = parseFloat(move.required_qty || 0);
                    const currentDone = parseFloat(move.qty_done || 0);
                    const needed = Math.max(0, currentReq - currentDone);

                    if (!lineObj.qty_done) {
                        const lotQty = parseFloat(autoLot.quantity || 0);
                        const fallbackNeeded = needed || currentReq || lotQty;
                        lineObj.qty_done = Math.min(fallbackNeeded, lotQty || fallbackNeeded);
                    }
                }
                */

                return lineObj;
            });

            move.move_lines.forEach((line) => {
                if (!line.lot_id) return;
                const alreadyListed = availableLots.find((lot) => lot.id === line.lot_id);
                if (!alreadyListed) {
                    availableLots.unshift({
                        id: line.lot_id,
                        name: line.lot_name || `Lot ${line.lot_id}`,
                        quantity: line.qty_done || 0,
                    });
                }
            });
            move.available_lots = availableLots;
            return move;
        });
        return picking;
    }

    _defaultPickingLine(move) {
        const remaining = Math.max(
            (move.required_qty || 0) - (move.qty_done || 0),
            0
        );
        return {
            id: null,
            client_id: this._generateClientLineId(move),
            lot_id: null,
            lot_name: "",
            qty_done: remaining || move.required_qty || 0,
            location_id: move.location_id || null,
        };
    }

    _generateClientLineId(move) {
        this._lineUid += 1;
        return `${move.move_id || "move"}_${this._lineUid}`;
    }

    _buildAutoPickingLines(move, availableLots) {
        const required = parseFloat(move.required_qty || "0") || 0;
        let remaining = required;
        const result = [];

        availableLots.forEach((lot, index) => {
            if (remaining <= 0) {
                return;
            }
            const lotQty = parseFloat(lot.quantity || 0) || 0;
            if (!lotQty) {
                return;
            }
            const qty = Math.min(lotQty, remaining);
            result.push({
                id: null,
                client_id: `${move.move_id}_${index}`,
                lot_id: lot.id,
                lot_name: lot.name,
                qty_done: qty,
                location_id: move.location_id || null,
            });
            remaining -= qty;
        });

        if (!result.length && required > 0) {
            result.push({
                id: null,
                client_id: `${move.move_id}_0`,
                lot_id: null,
                lot_name: "",
                qty_done: required,
                location_id: move.location_id || null,
            });
        }

        return result;
    }

    addPickingLine(move) {
        const newLine = this._defaultPickingLine(move);
        if (move.move_lines && move.move_lines.length > 0) {
            const firstLine = move.move_lines[0];
            if (firstLine.location_id) {
                newLine.location_id = firstLine.location_id;
            }
        }
        move.move_lines = [...move.move_lines, newLine];
    }

    _findLineIndex(move, line) {
        return (move.move_lines || []).indexOf(line);
    }

    removePickingLine(move, line) {
        const lines = [...move.move_lines];
        const index = this._findLineIndex(move, line);
        if (index === -1) {
            return;
        }
        if (lines.length <= 1) {
            lines[index] = this._defaultPickingLine(move);
        } else {
            lines.splice(index, 1);
        }
        move.move_lines = lines;
    }

    updatePickingLine(move, line, field, value) {
        const lines = [...move.move_lines];
        const index = this._findLineIndex(move, line);
        if (index === -1) {
            return;
        }
        const prevLine = { ...lines[index] };
        const newLine = { ...prevLine };
        if (field === "lot_name") {
            newLine.lot_name = value;
            newLine.lot_id = null;
        } else if (field === "qty_done") {
            newLine.qty_done = value;
        } else {
            if (field.endsWith("_id")) {
                if (value === "search_more") {
                    if (field === "location_id") {
                        this.openLocationSearch(move, prevLine);
                    } else if (field === "lot_id") {
                        this.openLotSearch(move, prevLine);
                    }
                    return;
                }
                if (value === "" || value === null || value === undefined) {
                    newLine[field] = null;
                } else {
                    const parsed = parseInt(value, 10);
                    newLine[field] = Number.isNaN(parsed) ? null : parsed;
                }
            } else {
                newLine[field] = value;
            }

            if (field === "location_id") {
                newLine.lot_id = null;
                newLine.lot_name = "";
                const lots = this.getAvailableLots(move, { ...newLine });
                if (this.requiresLot(move) && lots.length === 1) {
                    const autoLot = lots[0];
                    newLine.lot_id = autoLot.id;
                    newLine.lot_name = autoLot.name;
                    const otherLinesQty = lines.reduce((sum, l, idx) => {
                        return idx === index ? sum : sum + (parseFloat(l.qty_done) || 0);
                    }, 0);
                    const remainingNeeded = Math.max(
                        0,
                        (move.required_qty || 0) - otherLinesQty
                    );
                    const lotQty = parseFloat(autoLot.quantity || 0);
                    if (!newLine.qty_done || newLine.qty_done === 0) {
                        newLine.qty_done = Math.min(lotQty, remainingNeeded || lotQty);
                    }
                }
            }
        }
        lines[index] = newLine;

        if (index === 0 && field === "location_id") {
            const newLocId = newLine.location_id;
            for (let i = 1; i < lines.length; i++) {
                const otherLine = { ...lines[i] };
                otherLine.location_id = newLocId;
                otherLine.lot_id = null;
                otherLine.lot_name = "";

                lines[i] = otherLine;
            }
        }

        move.move_lines = lines;
    }

    selectPickingLot(move, line, lotId) {
        if (lotId === "search_more") {
            this.openLotSearch(move, line);
            return;
        }
        const id = parseInt(lotId, 10) || null;
        const lot = (move.available_lots || []).find((l) => l.id === id);
        const lines = [...move.move_lines];
        const index = this._findLineIndex(move, line);
        if (index === -1) {
            return;
        }
        const newLine = { ...lines[index] };
        newLine.lot_id = id;
        newLine.lot_name = lot ? lot.name : "";
        if (lot && lot.location_id) {
            newLine.location_id = lot.location_id;
        }

        if (lot) {
            const otherLinesQty = lines.reduce((sum, l, idx) => {
                return idx === index ? sum : sum + (parseFloat(l.qty_done) || 0);
            }, 0);

            const remainingNeeded = Math.max(0, (move.required_qty || 0) - otherLinesQty);

            const autoQty = Math.min(lot.quantity || 0, remainingNeeded);
            const currentQty = parseFloat(newLine.qty_done || 0);
            if (!currentQty || currentQty <= 0) {
                newLine.qty_done = autoQty;
            }
        }

        lines[index] = newLine;
        move.move_lines = lines;
    }

    getAvailableLocations(move) {
        return move.available_locations || [];
    }

    getAvailableLots(move, line) {
        const locId = line.location_id || move.location_id || null;
        if (!locId) {
            return [];
        }
        return (move.available_lots || []).filter(
            (lot) => lot.location_id === locId
        );
    }

    getOnHand(move, line) {
        const locId = line.location_id || null;
        if (!locId) {
            return "-";
        }
        if (this.requiresLot(move)) {
            const lots = this.getAvailableLots(move, line);
            if (!line.lot_id) {
                return "-";
            }
            const lot = lots.find((l) => l.id === line.lot_id);
            return lot ? lot.quantity : "-";
        }
        const loc = this.getAvailableLocations(move).find((l) => l.id === locId);
        return loc ? loc.on_hand : "-";
    }

    openLocationSearch(move, line) {
        const rootLoc = move.location_id || null;
        const domain = [["usage", "in", ["internal", "transit"]]];
        if (rootLoc) {
            domain.push(["id", "child_of", rootLoc]);
        }
        this.dialogService.add(SelectCreateDialog, {
            title: "Search: Location",
            resModel: "stock.location",
            domain,
            context: { active_test: true },
            onSelected: (ids) => {
                const id = (ids && ids[0]) || null;
                if (!id) {
                    return;
                }
                this.updatePickingLine(move, line, "location_id", id);
            },
        });
    }

    openLotSearch(move, line) {
        const locId = line.location_id || move.location_id || null;
        const domain = [
            ["product_id", "=", move.product_id],
            ["quantity", ">", 0],
        ];
        if (locId) {
            domain.push(["location_id", "child_of", locId]);
        }
        this.dialogService.add(SelectCreateDialog, {
            title: "Search: Lot / Quant",
            resModel: "stock.quant",
            domain,
            context: { active_test: true },
            onSelected: (ids) => {
                const id = (ids && ids[0]) || null;
                if (!id) {
                    return;
                }
                rpc("/web/dataset/call_kw/stock.quant/read", {
                    model: "stock.quant",
                    method: "read",
                    args: [[id], ["lot_id", "location_id", "quantity"]],
                    kwargs: {},
                }).then((rows) => {
                    const rec = rows && rows[0];
                    if (!rec) {
                        return;
                    }
                    const loc = rec.location_id && rec.location_id[0];
                    const lot = rec.lot_id && rec.lot_id[0];
                    if (loc) {
                        this.updatePickingLine(move, line, "location_id", loc);
                    }
                    if (lot) {
                        this.selectPickingLot(move, line, lot);
                    }
                });
            },
        });
    }

    requiresLot(move) {
        return ["lot", "serial"].includes(move.product_tracking);
    }

    async validatePicking() {
        const drawer = this.state.pickingDrawer;
        if (!drawer.picking) {
            return;
        }
        drawer.saving = true;

        try {
            const movesPayload = (drawer.picking.moves || []).map((move) => {
                const lines = (move.move_lines || [])
                    .map((line) => {
                        const qty = parseFloat(line.qty_done || "0") || 0;
                        return {
                            lot_id: line.lot_id || null,
                            lot_name: !line.lot_id ? line.lot_name || "" : line.lot_name,
                            qty_done: qty,
                            location_id: line.location_id || move.location_id || null,
                        };
                    })
                    .filter((line) => line.qty_done > 0);

                return {
                    move_id: move.move_id,
                    lines,
                };
            });

            const res = await rpc("/mrp_parallel_console/validate_picking", {
                picking_id: drawer.picking.id,
                moves: movesPayload,
            });

            if (res && res.error) {
                throw new Error(res.error);
            }

            const finalizeSuccess = async () => {
                this.notification.add("Picking validated.", { type: "success" });
                await this.loadData();
            };

            drawer.open = false;
            drawer.picking = null;
            drawer.availablePickings = [];
            drawer.activePickingId = null;

            if (res.action && typeof res.action === "object") {
                await this.actionService.doAction(res.action, {
                    onClose: finalizeSuccess,
                });
            } else {
                await finalizeSuccess();
            }
        } catch (error) {
            this.notification.add(
                error.message || "Failed to validate picking.",
                { type: "danger" }
            );
        } finally {
            drawer.saving = false;
        }
    }



    async openScrapModal(wo) {
        const ctx = await rpc("/mrp_parallel_console/get_scrap_context", {
            workorder_id: wo.id,
        });
        if (ctx.error) {
            this.notification.add(ctx.error, { type: "danger" });
            return;
        }

        const allProducts = ctx.products || [];
        // Default to 'component' tab
        const initialTab = 'component';
        const filtered = allProducts.filter(p => p.type === initialTab);
        const firstProduct = filtered.length ? filtered[0] : null;

        const workcenterName = wo.workcenter_name || wo.workcenter_id?.display_name || "";
        this.state.scrapModal = {
            open: true,
            workorder: wo,
            products: allProducts,
            filteredProducts: filtered,
            activeTab: initialTab,
            locations: ctx.locations || [],
            scrapLocations: ctx.scrap_locations || [],
            scrapReasons: ctx.scrap_reasons || [],
            productId: (firstProduct && firstProduct.id) || null,
            qty: 0,
            productId: (firstProduct && firstProduct.id) || null,
            qty: 0,
            defaultLocationId: ctx.default_location_id || null, // Store general default
            locationId: ctx.default_location_id || null, // Initial value
            scrapLocationId: ctx.default_scrap_location_id || null,
            scrapLocationId: ctx.default_scrap_location_id || null,
            scrapReasonId:
                (ctx.scrap_reasons && ctx.scrap_reasons[0] && ctx.scrap_reasons[0].id) ||
                null,
            reason: "",
            lotName: "",
            lotId: null,
            availableLots: (firstProduct && firstProduct.lots) || [],
            productType: (firstProduct && firstProduct.type) || "",
            workcenterDisplay: workcenterName,
        };
        if (firstProduct) {
            this._applyScrapProductDefaults(firstProduct);
        }
    }

    setScrapTab(tabName) {
        if (!this.state.scrapModal) return;
        this.state.scrapModal.activeTab = tabName;

        const allProducts = this.state.scrapModal.products || [];
        const filtered = allProducts.filter(p => p.type === tabName);
        this.state.scrapModal.filteredProducts = filtered;

        const firstProduct = filtered.length ? filtered[0] : null;
        this.state.scrapModal.productId = (firstProduct && firstProduct.id) || null;

        if (firstProduct) {
            this._applyScrapProductDefaults(firstProduct);
        } else {
            // Clear defaults if no product in this tab
            this.state.scrapModal.availableLots = [];
            this.state.scrapModal.productType = "";
            this.state.scrapModal.lotId = null;
            this.state.scrapModal.lotName = "";
        }
        // Reset quantity and reason when switching tabs to avoid sharing values
        this.state.scrapModal.qty = 0;
        this.state.scrapModal.reason = "";
    }

    async openScrapRecord(scrapId) {
        if (!scrapId) {
            return;
        }
        await this.actionService.doAction(
            {
                type: "ir.actions.act_window",
                res_model: "stock.scrap",
                res_id: scrapId,
                views: [[false, "form"]],
                target: "new",
                context: { create: false },
            },
            {
                onClose: async () => {
                    await this.loadData(this._productionId, { preserveSelection: true });
                    if (this.state.scrapModal?.workorder) {
                        const updatedWo = this.state.workorders.find(
                            (w) => w.id === this.state.scrapModal.workorder.id
                        );
                        if (updatedWo) {
                            this.state.scrapModal.workorder = updatedWo;
                        }
                    }
                },
            }
        );
    }

    closeScrapModal() {
        this.state.scrapModal.open = false;
    }

    scrapChange(field, value) {
        this.state.scrapModal[field] = value;
    }

    onScrapProductChange(ev) {
        const value = parseInt(ev.target.value, 10);
        const prodId = Number.isNaN(value) ? null : value;
        this.scrapChange("productId", prodId);
        const productMeta = (this.state.scrapModal.products || []).find(p => p.id === prodId);
        this._applyScrapProductDefaults(productMeta);
    }

    _applyScrapProductDefaults(productMeta) {
        if (!this.state.scrapModal) {
            return;
        }
        const lots = productMeta ? (productMeta.lots || []) : [];
        this.state.scrapModal.availableLots = lots;
        this.state.scrapModal.productType = productMeta ? productMeta.type : "";

        // Auto-select Source Location if provided (from controller logic)
        if (productMeta && productMeta.source_location_id) {
            this.state.scrapModal.locationId = productMeta.source_location_id;
        } else {
            // Fallback to default
            this.state.scrapModal.locationId = this.state.scrapModal.defaultLocationId;
        }

        // Auto-select Lot if default provided (e.g. for FG)
        if (productMeta && productMeta.type === "finished") {
            const finishedLot = productMeta.default_lot_id || null;
            this.state.scrapModal.lotId = finishedLot;
            this.state.scrapModal.lotName = productMeta.default_lot_name || "";
        } else if (productMeta && productMeta.type === "component" && lots.length) {
            this.state.scrapModal.lotId = lots[0].id;
            this.state.scrapModal.lotName = lots[0].name;
        } else {
            this.state.scrapModal.lotId = null;
            this.state.scrapModal.lotName = "";
        }
    }

    onScrapLocationChange(ev) {
        const value = parseInt(ev.target.value, 10);
        this.scrapChange("locationId", Number.isNaN(value) ? null : value);
    }

    onScrapScrapLocationChange(ev) {
        const value = parseInt(ev.target.value, 10);
        this.scrapChange("scrapLocationId", Number.isNaN(value) ? null : value);
    }

    onScrapReasonChange(ev) {
        const value = parseInt(ev.target.value, 10);
        this.scrapChange("scrapReasonId", Number.isNaN(value) ? null : value);
    }

    async saveScrapModal() {
        const m = this.state.scrapModal;
        const qty = parseFloat(m.qty || "0") || 0;
        if (!m.productId || qty <= 0) {
            this.notification.add(
                "Please select a product and a positive quantity.",
                { type: "warning" }
            );
            return;
        }
        const productMeta = (m.products || []).find((p) => p.id === m.productId);
        if (productMeta && typeof productMeta.max_qty === "number" && qty > productMeta.max_qty) {
            const label = productMeta.type === 'component' ? 'component' : 'finished product';
            this.notification.add(
                `Scrap quantity cannot exceed ${label} planned quantity (${productMeta.max_qty}).`,
                { type: "warning" }
            );
            return;
        }
        const res = await rpc("/mrp_parallel_console/create_scrap", {
            workorder_id: m.workorder.id,
            product_id: m.productId,
            quantity: qty,
            location_id: m.locationId,
            scrap_location_id: m.scrapLocationId,
            scrap_reason_tag_ids: m.scrapReasonId ? [m.scrapReasonId] : [],
            reason: m.reason,
            lot_id: m.lotId,
            lot_name: m.lotName,
            workcenter_name: m.workorder.workcenter_name || "",
        });
        if (res && res.status === "success") {
            this.notification.add(
                res.message || "Scrap saved (Draft). Validated on Close.",
                { type: "success" }
            );
            this.state.scrapModal.qty = 0;
            this.state.scrapModal.reason = "";
            if (this.scrapQtyRef.el) {
                this.scrapQtyRef.el.value = ""; // Ensure visual clear if binding lags
                this.scrapQtyRef.el.focus();
            }
            await this.loadData(this._productionId, { preserveSelection: true });
            const updatedWo = this.state.workorders.find(
                (w) => w.id === this.state.scrapModal.workorder.id
            );
            if (updatedWo) {
                this.state.scrapModal.workorder = updatedWo;
            }
        } else {
            this.notification.add(res.error || "Error creating scrap", {
                type: "danger",
            });
        }
    }

    onScrapLotChange(ev) {
        const lotId = parseInt(ev.target.value, 10) || null;
        if (!lotId) {
            this.state.scrapModal.lotId = null;
            return;
        }
        const lot = (this.state.scrapModal.availableLots || []).find(l => l.id === lotId);
        this.state.scrapModal.lotId = lotId;
        this.state.scrapModal.lotName = lot ? lot.name : "";
        if (lot && lot.location_id) {
            this.state.scrapModal.locationId = lot.location_id;
        }
    }


    async startWo(wo) {
        if (wo.is_locked) {
            let msg = "Machine is unavailable.";
            if (wo.machine_status === "maintenance") {
                msg = "Machine is under maintenance.";
            } else if (wo.machine_status === "busy") {
                msg = "Machine is busy with another order.";
            }
            this.notification.add(msg, { type: "danger" });
            return;
        }
        if (this.state.moClosed) {
            this.notification.add(
                "This manufacturing order is closed. Starting workorders is not allowed.",
                { type: "warning" }
            );
            return;
        }
        if (!this.state.canCloseProduction) {
            this.notification.add("Please pick components first.", { type: "warning" });
            return;
        }

        const targetIds = this.state.selectedIds.size
            ? Array.from(this.state.selectedIds)
            : [wo.id];

        const readyIds = [];
        const skippedNotReady = [];
        const skippedNoEmployees = [];
        const skippedLocked = [];
        for (const id of targetIds) {
            const card = this.state.workorders.find((w) => w.id === id);
            if (!card) {
                skippedNotReady.push(id);
                continue;
            }
            if (card.is_locked) {
                skippedLocked.push(id);
                continue;
            }
            if (card.state !== "ready") {
                skippedNotReady.push(id);
                continue;
            }
            if (!card.employees || !card.employees.length) {
                skippedNoEmployees.push(id);
                continue;
            }
            readyIds.push(id);
        }

        if (!readyIds.length) {
            let msg = _t("No workorders can be started.");
            if (skippedNoEmployees.length) {
                msg = _t("Please assign employees before starting.");
            } else if (skippedNotReady.length) {
                msg = _t("No selected workorders are in Ready state.");
            }
            this.notification.add(msg, { type: "warning" });
            return;
        }

        let startedCount = 0;
        let skippedMissingComponents = 0;
        let errorCount = 0;
        for (const id of readyIds) {
            const checkRes = await rpc("/mrp_parallel_console/check_components", {
                workorder_id: id,
            });
            if (checkRes && (!checkRes.sufficient || checkRes.error)) {
                skippedMissingComponents += 1;
                continue;
            }
            const res = await rpc("/mrp_parallel_console/start_workorder", { workorder_id: id });
            if (res && res.error) {
                errorCount += 1;
                continue;
            }
            const card = this.state.workorders.find((w) => w.id === id);
            if (card) {
                const nextState = res.state || card.state;
                const updates = {
                    console_date_start: res.start,
                    console_date_finished: null,
                    state: nextState,
                    state_label: this._getWorkorderStateLabel(nextState),
                };
                Object.assign(card, updates);
                this._syncActiveWo(card.id, updates);
            }
            startedCount += 1;
        }

        const skippedCount =
            skippedNotReady.length +
            skippedNoEmployees.length +
            skippedLocked.length +
            skippedMissingComponents +
            errorCount;

        if (startedCount && !skippedCount) {
            this.notification.add(_t("Started selected workorders."), { type: "success" });
            return;
        }

        if (startedCount) {
            const parts = [];
            if (skippedNoEmployees.length) {
                parts.push(`no employees: ${skippedNoEmployees.length}`);
            }
            if (skippedNotReady.length) {
                parts.push(`not ready: ${skippedNotReady.length}`);
            }
            if (skippedLocked.length) {
                parts.push(`locked: ${skippedLocked.length}`);
            }
            if (skippedMissingComponents) {
                parts.push(`missing components: ${skippedMissingComponents}`);
            }
            if (errorCount) {
                parts.push(`errors: ${errorCount}`);
            }
            const detail = parts.length ? ` (${parts.join(", ")})` : "";
            this.notification.add(`Started ${startedCount} workorders. Skipped ${skippedCount}${detail}.`, {
                type: "warning",
            });
            return;
        }

        // Nothing started
        if (skippedNoEmployees.length) {
            this.notification.add(_t("Please assign employees before starting."), {
                type: "warning",
            });
            return;
        }
        if (skippedMissingComponents) {
            this.notification.add(_t("Please pick components first."), { type: "warning" });
            return;
        }
        this.notification.add(_t("No workorders were started."), { type: "warning" });
    }

    async stopWo(wo) {
        const targetIds = this.state.selectedIds.size
            ? Array.from(this.state.selectedIds)
            : [wo.id];

        let stoppedCount = 0;
        let skippedCount = 0;
        let errorCount = 0;

        for (const id of targetIds) {
            const card = this.state.workorders.find((w) => w.id === id);
            if (!card) {
                skippedCount += 1;
                continue;
            }
            const isRunning = Boolean(card.console_date_start && !card.console_date_finished) || card.state === "progress";
            if (!isRunning) {
                skippedCount += 1;
                continue;
            }
            const res = await rpc("/mrp_parallel_console/stop_workorder", {
                workorder_id: id,
            });
            if (res && res.error) {
                this.notification.add(res.error, { type: "danger" });
                errorCount += 1;
                continue;
            }
            const updates = {
                console_date_finished:
                    res.end || card.console_date_finished || new Date().toISOString(),
                state: res.state || card.state,
                state_label: this._getWorkorderStateLabel(res.state || card.state),
            };
            Object.assign(card, updates);
            this._syncActiveWo(card.id, updates);
            stoppedCount += 1;
        }
        if (stoppedCount) {
            this.notification.add(`Stopped ${stoppedCount} workorder(s).`, { type: "success" });
        }
        if (skippedCount) {
            this.notification.add(`Skipped ${skippedCount} workorder(s) not running.`, { type: "warning" });
        }
        if (errorCount) {
            this.notification.add(`Errors on ${errorCount} workorder(s).`, { type: "danger" });
        }
    }

    async finishWo(wo) {
        if (this.state.moClosed) {
            this.notification.add(
                "This manufacturing order is closed. Finishing workorders is not allowed.",
                { type: "warning" }
            );
            return;
        }

        this.dialogService.add(ConfirmationDialog, {
            title: "Confirmation",
            body: `Mark workorder ${wo.name} as completed?`,
            confirm: async () => {
                try {
                    const res = await rpc("/mrp_parallel_console/finish_workorder", {
                        workorder_id: wo.id,
                    });

                    if (res && res.error) {
                        this.notification.add(res.error, { type: "danger" });
                        return;
                    }

                    // Update the card state
                    const card = this.state.workorders.find((w) => w.id === wo.id);
                    if (card) {
                        const nextState = res.state || "done";
                        const updates = {
                            state: nextState,
                            state_label: this._getWorkorderStateLabel(nextState),
                            console_date_finished: res.end || new Date().toISOString(),
                        };
                        Object.assign(card, updates);
                        this._syncActiveWo(card.id, updates);
                    }

                    this.notification.add("Workorder marked as done successfully.", { type: "success" });

                    // Reload workorder list
                    await this.reloadWorkorders();

                } catch (error) {
                    console.error("Error finishing workorder:", error);
                    this.notification.add(
                        error.message || "Failed to finish workorder.",
                        { type: "danger" }
                    );
                }
            },
            cancel: () => { },
        });
    }









    formatDisplayDatetime(value) {
        if (!value) {
            return "-";
        }
        try {
            const normalized = value.replace(" ", "T");
            const date = new Date(normalized + (normalized.includes('Z') ? '' : 'Z')); // Ensure UTC

            return date.toLocaleString('th-TH', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: false
            }).replace(',', '');
        } catch (e) {
            return value.replace("T", " ");
        }
    }

    formatInputDatetime(value) {
        if (!value) {
            return "";
        }
        const normalized = value.replace(" ", "T");
        return normalized.length > 16 ? normalized.slice(0, 16) : normalized;
    }

    parseDatetimeInput(value) {
        if (!value) {
            return false;
        }
        if (!value.includes("T")) {
            return value;
        }
        const [date, time] = value.split("T");
        if (!date || !time) {
            return false;
        }
        const fullTime = time.length === 5 ? `${time}:00` : time;
        return `${date} ${fullTime}`;
    }

    updateActiveDatetime(field, inputValue) {
        if (!this.state.activeWo) {
            return;
        }
        this.state.activeWo[field] = this.parseDatetimeInput(inputValue);
    }

    _syncActiveWo(woId, values) {
        if (this.state.activeWo && this.state.activeWo.id === woId) {
            Object.assign(this.state.activeWo, values);
        }
    }

    computeRemaining(wo) {
        const planned = parseFloat(wo.planned_qty || "0") || 0;
        const consoleQty = parseFloat(wo.console_qty || "0") || 0;
        const remaining = planned - consoleQty;
        return remaining > 0 ? remaining : 0;
    }


    async createQC(wo) {
        const res = await rpc("/mrp_parallel_console/create_quality_check", {
            workorder_id: wo.id,
        });

        if (res && res.error) {
            this.notification.add(res.error, { type: "danger" });
            return;
        }

        if (res && res.action) {
            await this.actionService.doAction(res.action, {
                onClose: async () => {
                    await this.loadData();
                },
            });
        } else if (res && res.warning) {
            this.notification.add(res.warning, { type: "warning" });
        } else {
            this.notification.add(
                "No quality control points found for this work order.",
                { type: "warning" }
            );
        }
    }
}
ParallelWorkorderConsole.template = "mrp_parallel_console.WorkorderConsole";
ParallelWorkorderConsole.props = { ...standardActionServiceProps };

actionRegistry.add("mrp_parallel_console.main_root", ParallelShopfloorHomeAction);
actionRegistry.add("mrp_parallel_console.main_console", ParallelWorkorderConsole);
