# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from collections import defaultdict

from dateutil.relativedelta import relativedelta
from odoo import _, fields, http
from odoo.exceptions import AccessError, UserError
from odoo.http import request
from odoo.osv import expression
from odoo.tools import float_compare, float_round

WORKORDER_NOT_FOUND = "Task not found."
MRP_WORKORDER_MODEL = "mrp.workorder"
MRP_PRODUCTION_MODEL = "mrp.production"
STOCK_PICKING_MODEL = "stock.picking"
STOCK_MOVE_MODEL = "stock.move"
STOCK_LOT_MODEL = "stock.lot"
STOCK_QUANT_MODEL = "stock.quant"



PICKING_PRINT_REPORTS = [
    (
        "stock.action_report_picking",
        "Picking Operations",
        "Internal picking list balancing demanded/available quantities.",
    ),
    (
        "stock.action_report_delivery",
        "Delivery Slip",
        "Customer-facing delivery document.",
    ),
    (
        "stock.action_report_picking_packages",
        "Packages Content",
        "Lists packages and their contents.",
    ),
    (
        "stock.action_report_picking_type_label",
        "Product Labels",
        "Generate product/lot labels for this transfer.",
    ),
]


def _selection_label(record, field_name, value):
    """Return the human-readable label for a selection value."""
    field = record._fields.get(field_name)
    if not field:
        return value
    selection = field.selection
    if callable(selection):
        selection = selection(record.env)
    lookup = dict(selection or [])
    val = lookup.get(value, value)

    translations = {
        "Waiting for another WO": "รอการผลิตก่อนหน้า",
        "Waiting for components": "รอวัตถุดิบ",
        "Ready": "พร้อมผลิต",
        "In Progress": "กำลังผลิต",
        "Finished": "เสร็จสิ้น",
        "Done": "เสร็จสิ้น",
        "Cancelled": "ยกเลิก"
    }
    return translations.get(val, val)


def _require_group(group_xmlid):
    """Require the requested group, falling back to internal user only."""
    user = request.env.user
    group_xmlid = group_xmlid or "base.group_user"
    if not user.has_group(group_xmlid):
        raise AccessError(_("You do not have permission to perform this action."))


class MrpParallelConsoleController(http.Controller):
    def _mpc_enforce_employee_breakdown(self):
        """Toggle employee breakdown enforcement via system parameter."""
        param = request.env["ir.config_parameter"].sudo().get_param(
            "mrp_parallel_console.enforce_employee_breakdown", "True"
        )
        return param == "True"

    def _mpc_get_workorder_mold_payload(self, workorder):
        payload = []
        for mold in workorder.mold_ids:
            limit = mold.mold_life_limit or 0
            current = mold.mold_life_current or 0
            payload.append(
                {
                    "id": mold.id,
                    "name": mold.display_name,
                    "state": getattr(mold, "mold_state", "normal") or "normal",
                    "life_current": current,
                    "life_limit": limit,
                    "life_remaining": (limit - current) if limit else False,
                    "cavities": mold.mold_cavities or 0,
                }
            )
        return payload

    def _mpc_should_show_mold_ui(self, workorder):
        if not request.env["mrp.workcenter"].is_mold_management_enabled():
            return False
        if hasattr(workorder, "mold_ids") and workorder.mold_ids:
            return True
        workcenter = workorder.workcenter_id
        if not workcenter:
            return False
        if "allowed_mold_ids" not in workcenter._fields:
            return False
        return bool(workcenter.allowed_mold_ids)

    def _mpc_get_mold_selection_action(self, workorder):
        ctx = {
            "active_id": workorder.id,
            "active_model": "mrp.workorder",
        }
        wizard = request.env["mrp.mold.selection.wizard"].with_context(ctx).create({})
        action = request.env["ir.actions.actions"]._for_xml_id(
            "mrp_mold_management.action_mrp_mold_selection_wizard"
        )
        action["res_id"] = wizard.id
        action["views"] = [[False, "form"]]
        action["view_mode"] = "form"
        action["target"] = "new"
        action["context"] = ctx
        return action

    def _mpc_get_alternative_mold_lines(
        self, workorder, exclude_mold_ids=None, exclude_full=True
    ):
        matrix_lines = request.env["mrp.mold.matrix.report"].search(
            [("product_id", "=", workorder.product_id.id)]
        )
        exclude_mold_ids = set(exclude_mold_ids or [])
        if exclude_mold_ids:
            matrix_lines = matrix_lines.filtered(
                lambda line: line.mold_id.id not in exclude_mold_ids
            )
        if exclude_full:
            matrix_lines = matrix_lines.filtered(lambda line: line.mold_state != "full")

        seen = set()
        alternatives = []
        sorted_lines = matrix_lines.sorted(
            key=lambda line: (
                0 if line.machine_id == workorder.workcenter_id else 1,
                0
                if line.mold_state == "normal"
                else 1 if line.mold_state == "warning" else 2,
                line.machine_id.display_name or "",
                line.mold_id.display_name or "",
            )
        )
        for line in sorted_lines:
            key = (line.machine_id.id, line.mold_id.id)
            if key in seen:
                continue
            seen.add(key)
            limit = line.mold_id.mold_life_limit or 0
            current = line.mold_id.mold_life_current or 0
            alternatives.append(
                {
                    "machine_id": line.machine_id.id,
                    "machine_name": line.machine_id.display_name,
                    "mold_id": line.mold_id.id,
                    "mold_name": line.mold_id.display_name,
                    "mold_state": line.mold_state or "normal",
                    "shots_remaining": (limit - current) if limit else False,
                    "cycle_time": line.cycle_time,
                    "units_per_hour": line.units_per_hour,
                }
            )
        return alternatives
    # ---------------------------------------------------------
    # Real-time notification helper
    # ---------------------------------------------------------
    @staticmethod
    def _broadcast_console_update(production_id, event_type, data):
        """
        Broadcast real-time update to all clients viewing this MO's console.

        Args:
            production_id: ID of the manufacturing order
            event_type: Event identifier (e.g., 'workorder_started', 'quantity_changed')
            data: Dictionary of event data to send to clients
        """
        if not production_id:
            return

        channel = f"mrp_parallel_console.production.{production_id}"
        try:
            request.env["bus.bus"]._sendone(channel, event_type, data)
        except Exception:
            # Log but don't fail the operation if bus notification fails
            pass

    # ---------------------------------------------------------
    # Root dashboard: list Manufacturing Orders
    # ---------------------------------------------------------
    @http.route("/mrp_parallel_console/get_mos", type="json", auth="user")
    def get_mos(self, domain=None, context=None):
        _require_group("mrp.group_mrp_user")
        production_model = request.env[MRP_PRODUCTION_MODEL]
        # Let the search view control state/domain; only enforce active picking type.
        base_domain = [("picking_type_id.active", "=", True), ("hide_from_shopfloor", "=", False)]
        if domain:
            try:
                full_domain = expression.AND([base_domain, domain])
            except Exception:
                full_domain = base_domain
        else:
            full_domain = base_domain
        mos = production_model.search(
            full_domain, order="date_start asc, bom_id asc, is_mto desc, priority desc, id desc", limit=80
        )
        current_user = request.env.user

        result = []
        for mo in mos:
            workorders = mo.workorder_ids
            finished_lot = getattr(mo, "final_lot_id", False) or mo.lot_producing_id
            rounding = mo.product_uom_id.rounding or 0.000001
            needs_backorder = (
                float_compare(
                    mo.qty_produced,
                    mo.product_qty,
                    precision_rounding=rounding,
                )
                < 0
            )
            has_open_wos = bool(
                workorders.filtered(
                    lambda w: w.state in ("ready", "progress", "pending", "waiting")
                )
            )
            can_manual_close = (
                mo.state == "to_close" and needs_backorder and not has_open_wos
            )
            result.append(
                {
                    "id": mo.id,
                    "name": mo.name,
                    "origin": mo.origin or "",
                    "user_id": mo.user_id.id,
                    "product": mo.product_id.display_name,
                    "qty": mo.product_qty,
                    "uom": mo.product_uom_id.display_name,
                    "state": mo.state,
                    "state_label": _selection_label(mo, "state", mo.state),
                    "workorder_count": len(workorders),
                    "ready_wo_count": len(
                        workorders.filtered(lambda w: w.state == "ready")
                    ),
                    "progress_wo_count": len(
                        workorders.filtered(lambda w: w.state == "progress")
                    ),
                    "done_wo_count": len(
                        workorders.filtered(lambda w: w.state == "done")
                    ),
                    "reservation_state": getattr(mo, "reservation_state", False),
                    "priority": mo.priority,
                    "components_availability_state": getattr(
                        mo, "components_availability_state", False
                    ),
                    "is_mine": mo.user_id and mo.user_id.id == current_user.id,
                    # UI flags
                    "can_confirm": mo.state == "draft",
                    "can_open_console": mo.state
                    in ("confirmed", "progress", "to_close"),
                    "can_manual_close": can_manual_close,
                    # Tracking / LOT info
                    "tracking": mo.product_id.tracking,
                    "has_lot": bool(finished_lot),
                    "lot_name": finished_lot.name or "",
                    # Custom Shopfloor info
                    "date_start": fields.Datetime.to_string(mo.date_start) if mo.date_start else "",
                    "is_mto": getattr(mo, "is_mto", False),
                }
            )
        return {"mos": result}

    # ---------------------------------------------------------
    # Data load for console (single MO)
    # ---------------------------------------------------------
    @http.route("/mrp_parallel_console/get_data", type="json", auth="user")
    def get_data(self, production_id=None):
        _require_group("mrp.group_mrp_user")
        if production_id:
            domain = [("production_id", "=", production_id), ("state", "!=", "cancel")]
        else:
            domain = [("state", "in", ["ready", "progress", "pending", "waiting", "draft"])]

        workorder_model = request.env[MRP_WORKORDER_MODEL]
        workorders = workorder_model.search(domain, order="id")

        if not workorders:
            return {
                "workorders": [],
                "can_close_production": True,
                "can_start_production": True,
                "production_state": False,
                "production_display": "",
                "mo_closed": False,
                "production_tracking": False,
                "production_lot_id": False,
                "production_lot_name": "",
                "mpc_supervisor_checked": False,
                "mpc_supervisor_name": False,
                "mpc_supervisor_check_date": False,
            }

        # 1. Prefetch basic related fields
        workorders.mapped("production_id")
        workorders.mapped("workcenter_id")
        workorders.mapped("employee_ids")
        workorders.mapped("mpc_employee_production_ids")
        if hasattr(workorder_model, "check_ids"):
            workorders.mapped("check_ids")
        if hasattr(workorder_model, "mold_ids"):
            workorders.mapped("mold_ids")

        productions = workorders.mapped("production_id")
        productions.mapped("move_raw_ids.move_line_ids")
        productions.mapped("product_id")

        # 2. Workcenter Status
        wc_ids = workorders.mapped("workcenter_id").ids
        busy_map = defaultdict(set)
        if wc_ids:
            progress_wos = workorder_model.search([("workcenter_id", "in", wc_ids), ("state", "=", "progress")])
            for pwo in progress_wos:
                busy_map[pwo.workcenter_id.id].add(pwo.id)

        maintenance_wcs = set()
        for wc in workorders.mapped("workcenter_id"):
            if getattr(wc, "maintenance_state", False) == "maintenance":
                maintenance_wcs.add(wc.id)
        if "maintenance.request" in request.env.registry and wc_ids:
            MaintReq = request.env["maintenance.request"]
            maint_domain = [("workcenter_id", "in", wc_ids)]
            if "state" in MaintReq._fields:
                maint_domain.append(("state", "not in", ["done", "cancel"]))
            elif "stage_id" in MaintReq._fields:
                stage_field = MaintReq._fields.get("stage_id")
                stage_model = getattr(stage_field, "comodel_name", False)
                if stage_model and "done" in request.env[stage_model]._fields:
                    maint_domain.append(("stage_id.done", "=", False))
            if "maintenance_type" in MaintReq._fields:
                maint_domain.append(("maintenance_type", "in", ["corrective", "preventive"]))
            maintenance_wcs |= set(MaintReq.search(maint_domain).mapped("workcenter_id.id"))

        # 3. Draft Scraps
        draft_scraps_map = defaultdict(list)
        draft_scraps = request.env["stock.scrap"].search([("workorder_id", "in", workorders.ids), ("state", "=", "draft")])
        for scrap in draft_scraps:
            draft_scraps_map[scrap.workorder_id.id].append(scrap)

        # 4. Qty Logs
        qty_logs_map = defaultdict(list)
        all_qty_logs = request.env["mrp.workorder.qty.log"].search([("workorder_id", "in", workorders.ids)], order="create_date asc, id asc")
        all_qty_logs.mapped("employee_ids")
        for log in all_qty_logs:
            qty_logs_map[log.workorder_id.id].append(log)

        # 5. Time Tracking (Productivity)
        time_tracking_map = defaultdict(list)
        Productivity = request.env.get("mrp.workcenter.productivity")
        if Productivity:
            all_prod_lines = Productivity.search([("workorder_id", "in", workorders.ids)], order="date_start desc, id desc")
            all_prod_lines.mapped("employee_id")
            for line in all_prod_lines:
                time_tracking_map[line.workorder_id.id].append(line)

        # 6. MO Component Summaries (Cached per MO) & Stock Availability
        products_by_loc = defaultdict(set)
        for mo in productions:
            if mo.location_src_id:
                for move in mo.move_raw_ids:
                    if move.state not in ("done", "cancel"):
                        products_by_loc[mo.location_src_id.id].add(move.product_id.id)

        quant_availability_map = {}
        Product = request.env["product.product"]
        for loc_id, prod_ids in products_by_loc.items():
            prods = Product.browse(list(prod_ids)).with_context(location=loc_id)
            for p in prods:
                quant_availability_map[(p.id, loc_id)] = p.qty_available

        mo_components_cache = {}
        for mo in productions:
            components = []
            production_ratio = 1.0
            if mo.qty_producing > 0 and mo.product_qty > 0:
                production_ratio = mo.qty_producing / mo.product_qty

            for move in mo.move_raw_ids:
                if move.state in ("done", "cancel"):
                    continue
                rounding = move.product_uom.rounding or 0.000001
                original_required = move.product_uom_qty
                required = float_round(original_required * production_ratio, precision_rounding=rounding)
                consumed = float_round(
                    sum(
                        getattr(ml, "qty_done", None) or getattr(ml, "quantity", 0.0) or 0.0
                        for ml in move.move_line_ids
                        if getattr(ml, "picked", True)
                    ),
                    precision_rounding=rounding,
                )
                remaining = max(float_round(required - consumed, precision_rounding=rounding), 0.0)
                components.append({
                    "product_id": move.product_id.id,
                    "product_name": move.product_id.display_name,
                    "required_qty": required,
                    "consumed_qty": consumed,
                    "remaining_qty": remaining,
                    "original_required": original_required,
                })
            mo_components_cache[mo.id] = components

        # BUILD RESULTS
        result = []
        production_state = None
        for wo in workorders:
            mo = wo.production_id
            production_state = production_state or mo.state
            components = mo_components_cache.get(mo.id, [])

            employees = [{"id": emp.id, "name": emp.name} for emp in wo.employee_ids]

            qty_logs = qty_logs_map.get(wo.id, [])
            qty_logs_sum = sum(log.qty for log in qty_logs)
            qty_logs_payload = [
                {
                    "id": log.id,
                    "qty": log.qty,
                    "note": log.note or "",
                    "create_date": log.create_date,
                    "log_date": log.log_date,
                    "employees": [{"id": emp.id, "name": emp.name} for emp in log.employee_ids],
                }
                for log in qty_logs
            ]

            employee_productions = [
                {
                    "id": ep.id,
                    "employee_id": ep.employee_id.id,
                    "employee_name": ep.employee_id.name,
                    "qty": ep.qty,
                }
                for ep in wo.mpc_employee_production_ids
            ]

            lot_name = ""
            if getattr(wo, "finished_lot_id", False):
                lot_name = wo.finished_lot_id.name
            elif getattr(mo, "lot_producing_id", False):
                lot_name = mo.lot_producing_id.name

            is_parallel = bool(getattr(wo.operation_id, "parallel_mode", False) == "parallel")
            planned_qty = wo.planned_qty if is_parallel and wo.planned_qty else mo.product_qty
            qc_pending = bool(
                getattr(wo, "check_ids", False)
                and wo.check_ids.filtered(lambda c: c.quality_state not in ("pass", "fail"))
            )

            time_tracking = []
            if Productivity:
                for line in time_tracking_map.get(wo.id, []):
                    duration = getattr(line, "duration", 0.0) or 0.0
                    hours = int(duration // 60)
                    minutes = int(round(duration % 60))
                    time_tracking.append({
                        "id": line.id,
                        "employee": getattr(line, "employee_id", False) and line.employee_id.display_name or "",
                        "duration": duration,
                        "duration_display": f"{hours:02d}:{minutes:02d}",
                        "start": getattr(line, "date_start", False),
                        "end": getattr(line, "date_end", False),
                        "productivity": getattr(line, "loss_id", False) and line.loss_id.display_name or "",
                    })

            scraps_data = []
            for s in draft_scraps_map.get(wo.id, []):
                p_type = "finished" if s.product_id == mo.product_id else "component"
                reason_text = ""
                if "scrap_reason_tag_ids" in s._fields and s.scrap_reason_tag_ids:
                    reason_text = ", ".join(s.scrap_reason_tag_ids.mapped("name"))
                elif hasattr(s, "scrap_reason_id") and s.scrap_reason_id:
                    reason_text = s.scrap_reason_id.display_name
                if not reason_text:
                    reason_text = getattr(s, "note", False) or getattr(s, "description", False) or (s.origin or "")
                scraps_data.append({
                    "id": s.id,
                    "name": s.name,
                    "product_name": s.product_id.display_name,
                    "qty": s.scrap_qty,
                    "uom": s.product_uom_id.display_name,
                    "reason": reason_text,
                    "type": p_type,
                })

            effective_qty = qty_logs_sum if qty_logs else (wo.console_qty or 0.0)

            # Fast Waiting check using pre-fetched availability
            display_state = wo.state
            if display_state == "waiting" and mo.location_src_id:
                for move in mo.move_raw_ids:
                    if move.state not in ("done", "cancel"):
                        avail = quant_availability_map.get((move.product_id.id, mo.location_src_id.id), 0.0)
                        if float_compare(avail, 0.0, precision_rounding=move.product_uom.rounding or 0.000001) > 0:
                            display_state = "ready"
                            break

            is_machine_busy = (
                wo.workcenter_id.id in busy_map
                and any(wid != wo.id for wid in busy_map[wo.workcenter_id.id])
                and wo.state != "progress"
            )

            result.append({
                "id": wo.id,
                "name": wo.name,
                "operation_name": wo.operation_id.name or "",
                "workcenter_name": wo.workcenter_id.display_name,
                "production_id": mo.id,
                "production_name": mo.display_name,
                "planned_qty": planned_qty,
                "console_qty": effective_qty,
                "qty_logs_sum": qty_logs_sum,
                "qty_logs": qty_logs_payload,
                "produced_qty": wo.qty_produced,
                "state": display_state,
                "state_label": _selection_label(wo, "state", display_state),
                "console_date_start": wo.console_date_start,
                "console_date_finished": wo.console_date_finished,
                "employees": employees,
                "components": components,
                "lot_name": lot_name,
                "scraps": scraps_data,
                "time_tracking": time_tracking,
                "production_tracking": mo.product_id.tracking,
                "machine_status": "maintenance" if wo.workcenter_id.id in maintenance_wcs else ("busy" if is_machine_busy else "available"),
                "is_locked": (wo.workcenter_id.id in maintenance_wcs) or is_machine_busy,
                "qc_pending": qc_pending,
                "mpc_require_employee_production": (wo.workcenter_id.mpc_require_employee_production and self._mpc_enforce_employee_breakdown()),
                "mpc_employee_production_ids": employee_productions,
                "employee_production_note": wo.mpc_employee_production_note or "",
                "mpc_supervisor_checked": wo.mpc_supervisor_checked,
                "mpc_supervisor_name": wo.mpc_supervisor_id.name if wo.mpc_supervisor_id else False,
                "mpc_supervisor_check_date": wo.mpc_supervisor_check_date,
                "show_mold_ui": self._mpc_should_show_mold_ui(wo),
                "molds": self._mpc_get_workorder_mold_payload(wo),
            })

        # Gating flags
        can_close_production = True
        can_start_production = True
        production = None
        if production_id:
            production = request.env[MRP_PRODUCTION_MODEL].browse(production_id)
        elif workorders:
            production = workorders[0].production_id

        if production and production.exists():
            pending_pickings = self._console_pending_pickings(production)
            if pending_pickings:
                can_close_production = False

        production_display = ""
        mo_closed = False
        production_tracking = None
        production_lot = False

        if production and production.exists():
            production_state = production.state
            production_display = production.display_name
            mo_closed = production_state in ("done", "cancel")
            can_start_production = not mo_closed
            production_tracking = production.product_id.tracking
            production_lot = getattr(production, "final_lot_id", False) or production.lot_producing_id

        return {
            "workorders": result,
            "can_close_production": can_close_production,
            "can_start_production": can_start_production,
            "production_state": production_state,
            "production_display": production_display,
            "mo_closed": mo_closed,
            "production_tracking": production_tracking,
            "production_lot_id": production_lot.id if production_lot else False,
            "production_lot_name": production_lot.name if production_lot else "",
            "mpc_supervisor_checked": production.mpc_supervisor_checked if production and production.exists() else False,
            "mpc_supervisor_name": production.mpc_supervisor_id.name if production and production.exists() and production.mpc_supervisor_id else False,
            "mpc_supervisor_check_date": fields.Datetime.to_string(production.mpc_supervisor_check_date) if production and production.exists() and production.mpc_supervisor_check_date else False,
        }
    # ---------------------------------------------------------
    # Update console fields (qty, dates, employees)
    # ---------------------------------------------------------
    @http.route("/mrp_parallel_console/update_console", type="json", auth="user")
    def update_console(self, lines):
        _require_group("mrp.group_mrp_user")
        workorder_model = request.env[MRP_WORKORDER_MODEL]

        for line in lines or []:
            self._process_console_line(workorder_model, line)

        return {"status": "ok"}

    @http.route("/mrp_parallel_console/save_employee_productions", type="json", auth="user")
    def save_employee_productions(self, workorder_id, note, productions):
        _require_group("mrp.group_mrp_user")
        workorder = request.env[MRP_WORKORDER_MODEL].browse(workorder_id)
        if not workorder.exists():
            return {"error": WORKORDER_NOT_FOUND}

        EmpQty = request.env["mrp.workorder.employee.qty"]
        existing_recs = {ep.employee_id.id: ep for ep in workorder.mpc_employee_production_ids}

        for p in productions:
            emp_id = p.get("employee_id")
            qty = p.get("qty", 0.0)
            if not emp_id:
                continue

            if emp_id in existing_recs:
                existing_recs[emp_id].write({"qty": qty})
            else:
                EmpQty.create({
                    "workorder_id": workorder.id,
                    "employee_id": emp_id,
                    "qty": qty,
                })

        workorder.write({"mpc_employee_production_note": note or ""})

        return {
            "status": "ok",
            "mpc_employee_production_ids": [
                {
                    "id": ep.id,
                    "employee_id": ep.employee_id.id,
                    "employee_name": ep.employee_id.name,
                    "qty": ep.qty,
                }
                for ep in workorder.mpc_employee_production_ids
            ],
            "employee_production_note": workorder.mpc_employee_production_note or "",
        }

    def _process_console_line(self, workorder_model, line):
        wo_id = line.get("id")
        if not wo_id:
            return

        wo = workorder_model.browse(wo_id)
        if not wo.exists():
            return

        vals = self._prepare_console_vals(line)
        if vals:
            wo.write(vals)

        self._update_console_employees(wo, line)

    # ---------------------------------------------------------
    # Quantity log (per batch/shift) -> sums into console_qty
    # ---------------------------------------------------------
    @http.route("/mrp_parallel_console/add_qty_log", type="json", auth="user")
    def add_qty_log(self, workorder_id, qty, note=None, employee_ids=None):
        _require_group("mrp.group_mrp_user")
        workorder = request.env[MRP_WORKORDER_MODEL].browse(workorder_id)
        if not workorder.exists():
            return {"error": WORKORDER_NOT_FOUND}
        if workorder.state == "cancel":
            return {"error": _("Cancelled workorders cannot receive output logs.")}

        try:
            qty_val = float(qty or 0.0)
        except Exception:
            qty_val = 0.0
        if qty_val <= 0:
            return {"error": _("Quantity must be greater than zero.")}

        # Automatically use the logged-in user's name if note is empty, "Unknown User", or matches the DB name
        if getattr(request.env, "cr", False) and getattr(request.env.cr, "dbname", False):
            db_name = str(request.env.cr.dbname)
        else:
            db_name = "pro"
        note_str = str(note or "").strip()
        if not note_str or note_str in ["Unknown User", "Unknown", db_name, "False"]:
            note = request.env.user.name

        # Prefer the latest time-tracking end date (Start/Stop timer) when WO is not running.
        # This keeps Output History and Finished At aligned with the "End Date" shown in Time Logs.
        log_date = False
        if workorder.state != "progress":
            Productivity = request.env.get("mrp.workcenter.productivity")
            if Productivity:
                last_prod = Productivity.search(
                    [
                        ("workorder_id", "=", workorder.id),
                        ("date_end", "!=", False),
                    ],
                    order="date_end desc, id desc",
                    limit=1,
                )
                if last_prod and last_prod.date_end:
                    log_date = last_prod.date_end
        if not log_date:
            log_date = workorder.console_date_finished or fields.Datetime.now()
        log_model = request.env["mrp.workorder.qty.log"]
        log_model.create(
            {
                "workorder_id": workorder.id,
                "log_date": log_date,
                "qty": qty_val,
                "note": note or "",
                "employee_ids": [
                    (
                        6,
                        0,
                        employee_ids
                        if employee_ids is not None
                        else workorder.employee_ids.ids,
                    )
                ],
            }
        )
        # Verify if we need to auto-create productivity lines (if not manual)
        # Use end date (console finished) when available to align output time with time logs.
        self._create_productivity_snapshot(
            workorder,
            employee_ids if employee_ids is not None else workorder.employee_ids.ids,
            log_date=log_date,
        )
        return self._get_qty_status(workorder)

    @http.route("/mrp_parallel_console/update_qty_log", type="json", auth="user")
    def update_qty_log(self, log_id, qty, note=None, employee_ids=None):
        _require_group("mrp.group_mrp_user")
        log = request.env["mrp.workorder.qty.log"].browse(log_id)
        if not log.exists():
            return {"error": _("Output record not found.")}
        try:
            qty_val = float(qty or 0.0)
        except Exception:
            qty_val = 0.0
        if qty_val <= 0:
            return {"error": _("Quantity must be greater than zero.")}
        vals = {"qty": qty_val, "note": note or ""}
        if employee_ids is not None:
            vals["employee_ids"] = [(6, 0, employee_ids)]
        log.write(vals)
        workorder = log.workorder_id
        return self._get_qty_status(workorder)

    @http.route(
        "/mrp_parallel_console/get_time_tracking_action", type="json", auth="user"
    )
    def get_time_tracking_action(
        self, workorder_id, employee_ids=None, log_date=None, start=None, end=None
    ):
        _require_group("mrp.group_mrp_user")
        workorder = request.env[MRP_WORKORDER_MODEL].browse(workorder_id)
        if not workorder.exists():
            return {"error": WORKORDER_NOT_FOUND}
        domain = [("workorder_id", "=", workorder.id)]
        window_start = None
        window_end = None
        try:
            if start:
                window_start = fields.Datetime.from_string(start)
            if end:
                window_end = fields.Datetime.from_string(end)
        except Exception:
            window_start = None
            window_end = None

        if not (window_start and window_end) and log_date:
            try:
                dt = fields.Datetime.from_string(log_date)
                window_start = dt - relativedelta(seconds=10)
                window_end = dt + relativedelta(seconds=10)
            except Exception:
                pass

        # Legacy fallback logic removed to ensure full history visibility.
        if not window_end:
            window_end = fields.Datetime.now()

        if window_start:
            domain.append(("date_end", ">=", window_start))
        if window_end:
            domain.append(("date_start", "<=", window_end))

        # Use our specific view that shows Employee instead of User
        view_id = request.env.ref(
            "mrp_parallel_console.view_mrp_workcenter_productivity_tree_parallel_console"
        ).id

        action = {
            "type": "ir.actions.act_window",
            "name": _("Time Logs"),
            "res_model": "mrp.workcenter.productivity",
            "views": [[view_id, "list"], [False, "form"]],
            "domain": domain,
            "context": {"default_workorder_id": workorder.id},
            "target": "new",
        }
        return {"action": action}

    def _get_effective_console_qty(self, workorder):
        """Compute effective console quantity from logs, fallback to field."""
        if workorder.state == "cancel":
            return 0.0
        logs = request.env["mrp.workorder.qty.log"].search(
            [("workorder_id", "=", workorder.id)]
        )
        if logs:
            return sum(logs.mapped("qty"))
        return workorder.console_qty or 0.0

    def _get_qty_status(self, workorder):
        """Helper to compute current Quantity status and payload."""
        logs = request.env["mrp.workorder.qty.log"].search(
            [("workorder_id", "=", workorder.id)], order="create_date asc, id asc"
        )
        total = self._get_effective_console_qty(workorder)
        workorder.console_qty = total
        logs_payload = [
            {
                "id": log_entry.id,
                "qty": log_entry.qty,
                "note": log_entry.note or "",
                "create_date": log_entry.create_date,
                "log_date": log_entry.log_date,
                "employees": [
                    {"id": emp.id, "name": emp.name} for emp in log_entry.employee_ids
                ],
            }
            for log_entry in logs
        ]
        return {
            "status": "ok",
            "workorder_id": workorder.id,
            "total": total,
            "logs": logs_payload,
        }

    def _create_productivity_snapshot(self, workorder, employee_ids, log_date=None):
        """Create a short productivity line per employee for visibility in Time Tracking."""
        if not employee_ids:
            return
        Productivity = request.env["mrp.workcenter.productivity"]
        Loss = request.env["mrp.workcenter.productivity.loss"]
        productive_loss = Loss.search([("loss_type", "=", "productive")], limit=1)
        now = log_date or fields.Datetime.now()

        # Check for overlapping/recent time logs to avoid double-counting
        # If the user is using the manual Start/Stop timer, or just logged output recently,
        # we assume the time cost is already covered.
        recent_domain = [
            ("workorder_id", "=", workorder.id),
            "|",
            ("date_end", "=", False),  # Timer is currently running
            (
                "date_end",
                ">=",
                now - relativedelta(minutes=5),
            ),  # Timer finished recently
        ]
        if Productivity.search_count(recent_domain):
            return

        # Use the same timestamp for start and end to create a "point in time" marker
        # rather than a 1-minute duration. This ensures the time log timestamp
        # precisely matches the output log creation time.
        vals_list = []
        for emp_id in employee_ids:
            vals = {
                "workorder_id": workorder.id,
                "workcenter_id": workorder.workcenter_id.id,
                "employee_id": emp_id,
                "date_start": now,
                "date_end": now,  # Same as start for zero duration
                "description": _("Auto log (Output)"),
            }
            if productive_loss:
                vals["loss_id"] = productive_loss.id
            vals_list.append(vals)
        if vals_list:
            Productivity.create(vals_list)

    @http.route("/mrp_parallel_console/toggle_supervisor_check", type="json", auth="user")
    def toggle_supervisor_check(self, workorder_id, checked):
        _require_group("mrp.group_mrp_user")
        workorder = request.env[MRP_WORKORDER_MODEL].browse(workorder_id)
        if not workorder.exists():
            return {"error": WORKORDER_NOT_FOUND}

        current_user = request.env.user
        now = fields.Datetime.now()

        vals = {
            "mpc_supervisor_checked": checked,
            "mpc_supervisor_id": current_user.id if checked else False,
            "mpc_supervisor_check_date": now if checked else False,
        }
        workorder.write(vals)

        return {
            "status": "ok",
            "mpc_supervisor_checked": workorder.mpc_supervisor_checked,
            "mpc_supervisor_name": current_user.name if checked else False,
            "mpc_supervisor_check_date": fields.Datetime.to_string(now) if checked else False,
        }

    @http.route("/mrp_parallel_console/toggle_mo_supervisor_check", type="json", auth="user")
    def toggle_mo_supervisor_check(self, production_id, checked):
        _require_group("mrp.group_mrp_user")
        production = request.env[MRP_PRODUCTION_MODEL].browse(production_id)
        if not production.exists():
            return {"error": _("Manufacturing Order not found.")}

        current_user = request.env.user
        now = fields.Datetime.now()

        vals = {
            "mpc_supervisor_checked": checked,
            "mpc_supervisor_id": current_user.id if checked else False,
            "mpc_supervisor_check_date": now if checked else False,
        }
        production.write(vals)

        if checked:
            from markupsafe import Markup
            msg = Markup(_("<b>✅ ตรวจสอบความถูกต้อง (Supervisor Verified)</b><br/>โดย: %s<br/>เวลา: %s")) % (
                current_user.name,
                fields.Datetime.to_string(now)
            )
            production.message_post(body=msg)

        return {
            "status": "ok",
            "mpc_supervisor_checked": production.mpc_supervisor_checked,
            "mpc_supervisor_name": current_user.name if checked else False,
            "mpc_supervisor_check_date": fields.Datetime.to_string(now) if checked else False,
        }

    @staticmethod
    def _prepare_console_vals(line):
        vals = {}
        if "console_qty" in line:
            vals["console_qty"] = line["console_qty"] or 0.0
        if line.get("console_date_start"):
            vals["console_date_start"] = line["console_date_start"]
        if line.get("console_date_finished"):
            vals["console_date_finished"] = line["console_date_finished"]
        return vals

    @staticmethod
    def _update_console_employees(workorder, line):
        emp_ids = line.get("employee_ids")
        if emp_ids is not None:
            workorder.action_console_set_employees(emp_ids)

    def _mpc_validate_component_scraps(self, productions):
        """Validate component scraps (stock.scrap) before closing productions.

        Goal: ensure component scraps are applied (stock deducted) before the MO close/consumption,
        but keep the console flow smooth by skipping scraps that cannot be validated
        (e.g., insufficient stock, missing lot).

        Returns a dict with summary counts and a small sample of skipped scraps.
        """
        registry = request.env.registry
        if "stock.scrap" not in registry:
            return {
                "scrap_validated_count": 0,
                "scrap_skipped_count": 0,
                "scrap_skipped": [],
            }

        Scrap = request.env["stock.scrap"]
        validated_count = 0
        skipped = []

        for mo in productions:
            raw_product_ids = set(
                mo.move_raw_ids.filtered(lambda m: m.state != "cancel")
                .mapped("product_id")
                .ids
            )
            if not raw_product_ids:
                continue

            scraps = Scrap.search(
                [
                    ("production_id", "=", mo.id),
                    ("state", "=", "draft"),
                ]
            )
            component_scraps = scraps.filtered(
                lambda s, raw_ids=raw_product_ids: s.product_id.id in raw_ids
            )

            for scrap in component_scraps:
                try:
                    can_validate = True
                    if hasattr(scrap, "check_available_qty"):
                        can_validate = bool(scrap.check_available_qty())

                    if not can_validate:
                        skipped.append(
                            {
                                "id": scrap.id,
                                "name": scrap.display_name,
                                "reason": "insufficient_stock",
                            }
                        )
                        continue

                    res = (
                        scrap.action_validate()
                        if hasattr(scrap, "action_validate")
                        else False
                    )
                    if isinstance(res, dict):
                        # stock.scrap.action_validate() may return an action (insufficient qty wizard)
                        skipped.append(
                            {
                                "id": scrap.id,
                                "name": scrap.display_name,
                                "reason": "insufficient_stock",
                            }
                        )
                        continue

                    if scrap.state == "done":
                        validated_count += 1
                    else:
                        skipped.append(
                            {
                                "id": scrap.id,
                                "name": scrap.display_name,
                                "reason": "not_validated",
                            }
                        )
                except (UserError, AccessError) as exc:
                    skipped.append(
                        {
                            "id": scrap.id,
                            "name": scrap.display_name,
                            "reason": str(exc),
                        }
                    )
                except Exception as exc:
                    skipped.append(
                        {
                            "id": scrap.id,
                            "name": scrap.display_name,
                            "reason": str(exc),
                        }
                    )

        return {
            "scrap_validated_count": validated_count,
            "scrap_skipped_count": len(skipped),
            "scrap_skipped": skipped[:10],
        }


    # ---------------------------------------------------------
    # Apply console: quantities + MRP logic + backorder
    # ---------------------------------------------------------
    @http.route("/mrp_parallel_console/apply_console", type="json", auth="user")
    def apply_console(self, workorder_ids):
        _require_group("mrp.group_mrp_user")
        workorder_model = request.env[MRP_WORKORDER_MODEL]
        wos = workorder_model.browse(workorder_ids or [])
        if not wos:
            return {"status": "empty"}

        productions = wos.mapped("production_id")
        finished_qty_map = {}
        for mo in productions:
            selected_wos = wos.filtered(lambda w, current_mo=mo: w.production_id == current_mo)
            finished_qty_map[mo.id] = mo._console_compute_total_qty(selected_wos)

        for mo in productions:
            mo._console_sync_component_overconsumption()

        # Overproduction must expand BOM demand and reserve additional
        # component lots before the lot prerequisite check below. Otherwise the
        # check compares the larger finished quantity against the old reserved
        # component lines and blocks valid overproduction flows too early.
        for mo in productions:
            total_qty = finished_qty_map.get(mo.id, 0.0)
            rounding = mo.product_uom_id.rounding or 0.000001
            if float_compare(total_qty, mo.product_qty, precision_rounding=rounding) > 0:
                mo._console_sync_demand_and_replenish(total_qty)

        # Validate all lot prerequisites before mutating WO state so the console
        # does not leave workorders done while the MO is still blocked on lots.
        for mo in productions:
            if (
                mo.product_tracking in ("lot", "serial")
                and not mo.lot_producing_id
                and not mo.workorder_ids.filtered("finished_lot_id")
            ):
                return {
                    "status": "lot_required",
                    "action": self._console_get_assign_lot_action(mo),
                }

        missing_lot_names = self._get_missing_lot_names(
            productions, finished_qty_map=finished_qty_map
        )
        if missing_lot_names:
            error_msg = _("Insufficient lots for components: %s. Please review lots.") % missing_lot_names
            return {
                "status": "missing_component_lots",
                "error": error_msg,
            }

        pending = wos.filtered(lambda wo: wo.state != "done")
        finish_errors = []
        for wo in pending:
            try:
                self._finish_single_workorder(wo)
            except UserError as exc:
                finish_errors.append(str(exc))
            except Exception as exc:
                finish_errors.append(
                    _("Failed to finish %(wo)s: %(msg)s")
                    % {"wo": wo.display_name, "msg": str(exc)}
                )
        remaining = wos.filtered(lambda wo: wo.state != "done")
        if remaining:
            names = ", ".join(remaining.mapped("display_name"))
            error_msg = (
                finish_errors[0]
                if finish_errors
                else _(
                    "Please finish all work orders before closing the manufacturing order. Pending: %s"
                )
                % names
            )
            return {
                "status": "workorders_pending",
                "error": error_msg,
            }

        # Ensure any running timers are stopped before closing
        running_wos = wos.filtered(
            lambda wo: wo.console_date_start and not wo.console_date_finished
        )
        if running_wos:
            running_wos.action_console_stop_timer()

        # Validate component scraps before closing to deduct stock correctly (skip if unavailable).
        scrap_summary = self._mpc_validate_component_scraps(productions)

        action = False
        company = productions[:1].company_id if productions else request.env.company
        for mo in productions:
            res = mo._console_apply_quantities_and_backorder(
                wos.filtered(lambda w, mo=mo: w.production_id == mo)
            )
            if res and not action:
                action = res

        # After applying quantities/backorders, surface QC if policy requires
        if company.mpc_qc_block_close:
            qc_action = self._mpc_get_pending_quality_action(productions, wos)
            if qc_action:
                return {
                    "status": "quality_pending",
                    "action": qc_action,
                    "post_close": True,
                }

        return {"status": "ok", "action": action, **scrap_summary}

    # ---------------------------------------------------------
    def _get_missing_lot_names(self, productions, finished_qty_map=None):
        """Check if any tracked components are missing lots for the given production qty."""
        finished_qty_map = finished_qty_map or {}
        missing_names = []
        for mo in productions:
            production_ratio = 1.0
            target_qty = finished_qty_map.get(mo.id, mo.qty_producing)
            if target_qty > 0 and mo.product_qty > 0:
                production_ratio = target_qty / mo.product_qty

            for move in mo.move_raw_ids.filtered(lambda m: m.state not in ("done", "cancel")):
                if move.product_id.tracking not in ("lot", "serial"):
                    continue

                rounding = move.product_uom.rounding or 0.000001
                # Expected consumed qty based on MO's qty_producing ratio
                expected = float_round(move.product_uom_qty * production_ratio, precision_rounding=rounding)

                # Currently assigned lots in move lines
                assigned = sum(move.move_line_ids.filtered(lambda line: line.lot_id or line.lot_name).mapped("quantity"))

                if float_compare(assigned, expected, precision_rounding=rounding) < 0:
                    missing_names.append(move.product_id.display_name)

        return ", ".join(set(missing_names)) if missing_names else False

    @http.route("/mrp_parallel_console/prepare_material_lots", type="json", auth="user")
    def prepare_material_lots(self, production_id=None):
        _require_group("mrp.group_mrp_user")
        if not production_id:
            return {"error": _("No manufacturing order found.")}

        production = request.env[MRP_PRODUCTION_MODEL].browse(production_id)
        if not production.exists():
            return {"error": _("Manufacturing order not found.")}

        return {
            "status": "ok",
            "target_qty": production.qty_producing or 0.0,
            "warning": False,
        }

    # ---------------------------------------------------------
    # Delete workorder from console (remove machine)
    # ---------------------------------------------------------
    @http.route("/mrp_parallel_console/delete_workorder", type="json", auth="user")
    def delete_workorder(self, workorder_id):
        _require_group("mrp.group_mrp_user")
        Workorder = request.env[MRP_WORKORDER_MODEL]
        Productivity = request.env["mrp.workcenter.productivity"]

        wo = Workorder.browse(workorder_id)
        if not wo.exists():
            return {"error": WORKORDER_NOT_FOUND}

        if wo.state in ("progress", "done", "cancel"):
            return {
                "error": _(
                    "You cannot remove this work order because it is in state %s."
                )
                % (wo.state,)
            }

        if wo.qty_produced:
            return {
                "error": _(
                    "You cannot remove this work order because some quantity has already been produced."
                )
            }

        has_time = Productivity.search_count([("workorder_id", "=", wo.id)]) > 0
        if has_time:
            return {
                "error": _(
                    "You cannot remove this work order because time tracking entries already exist."
                )
            }

        mo = wo.production_id
        wo.unlink()

        return {
            "status": "ok",
            "message": _(
                "Workcenter removed successfully. Quantities were rebalanced."
            ),
            "production_id": mo.id,
        }

    # ---------------------------------------------------------
    # Global employee list for console modal
    # ---------------------------------------------------------
    @http.route("/mrp_parallel_console/get_employees", type="json", auth="user")
    def get_employees(self, search=None, limit=80):
        _require_group("mrp.group_mrp_user")
        domain = [("active", "=", True)]
        if search:
            domain += ["|", ("name", "ilike", search), ("barcode", "ilike", search)]
        employee_model = request.env["hr.employee"]
        employees = employee_model.search(domain, limit=limit)
        return [{"id": emp.id, "name": emp.name} for emp in employees]

    @http.route("/mrp_parallel_console/assign_employees", type="json", auth="user")
    def assign_employees(self, workorder_ids=None, employee_ids=None):
        _require_group("mrp.group_mrp_user")
        workorder_model = request.env[MRP_WORKORDER_MODEL]
        employee_model = request.env["hr.employee"]

        workorders = workorder_model.browse(workorder_ids or [])
        if not workorders:
            return {"error": "Please select at least one workorder."}

        requested_ids = employee_ids or []
        employees = employee_model.browse(requested_ids)
        clear_all = not requested_ids
        if not clear_all and not employees:
            return {"error": "Please select at least one employee."}

        employee_ids = employees.ids if employees else []
        for wo in workorders:
            if clear_all:
                wo.action_console_set_employees([])
            else:
                current = set(wo.employee_ids.ids)
                combined = current | set(employee_ids)
                wo.action_console_set_employees(list(combined))

        message = (
            "Employees removed successfully."
            if not employees
            else "Employees assigned successfully. Click 'Start' button to begin work."
        )

        return {
            "status": "ok",
            "message": message,
            "mo_closed": all(
                wo.production_id.state in ("done", "cancel") for wo in workorders
            ),
        }

    # ---------------------------------------------------------
    # Scrap tools
    # ---------------------------------------------------------
    @http.route("/mrp_parallel_console/get_scrap_context", type="json", auth="user")
    def get_scrap_context(self, workorder_id):
        _require_group("mrp.group_mrp_user")
        workorder = request.env[MRP_WORKORDER_MODEL].browse(workorder_id)
        if not workorder.exists():
            return {"error": WORKORDER_NOT_FOUND}

        production = workorder.production_id
        products = []
        finished_lot = production.lot_producing_id
        if production.product_id:
            finished_max = (
                getattr(production, "qty_produced", False)
                or production.product_qty
                or 0.0
            )
            products.append(
                {
                    "id": production.product_id.id,
                    "name": production.product_id.display_name,
                    "type": "finished",
                    "max_qty": finished_max,
                    "default_lot_id": finished_lot.id if finished_lot else False,
                    "default_lot_name": finished_lot.display_name
                    if finished_lot
                    else "",
                    "source_location_id": production.location_dest_id.id
                    if production.location_dest_id
                    else False,
                    "uom_name": production.product_uom_id.name,
                }
            )
        for move in production.move_raw_ids:
            # For components: Use move location or production source location
            src_loc = (
                move.location_id.id
                if move.location_id
                else (
                    production.location_src_id.id
                    if production.location_src_id
                    else False
                )
            )
            products.append(
                {
                    "id": move.product_id.id,
                    "name": move.product_id.display_name,
                    "type": "component",
                    "max_qty": move.product_uom_qty,
                    "default_lot_id": False,
                    "default_lot_name": "",
                    "source_location_id": src_loc,
                    "uom_name": move.product_uom.name,
                }
            )

        unique_products = []
        seen = set()
        for p in products:
            if p["id"] in seen:
                continue
            seen.add(p["id"])
            unique_products.append(p)

        location_model = request.env["stock.location"]
        scrap_locs = location_model.search([("scrap_location", "=", True)])
        internal_locs = location_model.search([("usage", "=", "internal")])
        default_src = production.location_src_id or production.location_id

        quant_model = request.env[STOCK_QUANT_MODEL]
        product_model = request.env["product.product"]

        move_lines_map = {}
        for move in production.move_raw_ids:
            prod_id = move.product_id.id
            if prod_id not in move_lines_map:
                move_lines_map[prod_id] = request.env["stock.move.line"]
            move_lines_map[prod_id] |= move.move_line_ids

        product_lots_map = {}
        for p in unique_products:
            prod = product_model.browse(p["id"])
            lots = []
            if not prod.exists() or prod.tracking not in ("lot", "serial"):
                product_lots_map[p["id"]] = []
                continue

            if p.get("type") == "finished" and finished_lot:
                lots = [
                    {
                        "id": finished_lot.id,
                        "name": finished_lot.display_name,
                        "quantity": getattr(
                            finished_lot, "product_qty", production.product_qty
                        )
                        or 0.0,
                    }
                ]
            elif p.get("type") == "component":
                lines = move_lines_map.get(p["id"], request.env["stock.move.line"])
                lot_data = {}
                for line in lines:
                    if not line.lot_id:
                        continue
                    qty_line = (
                        line.qty_done if "qty_done" in line._fields else line.quantity
                    )
                    entry = lot_data.setdefault(
                        line.lot_id.id,
                        {
                            "id": line.lot_id.id,
                            "name": line.lot_id.name,
                            "location_id": line.location_id.id,
                            "quantity": 0.0,
                        },
                    )
                    entry["quantity"] += qty_line or 0.0
                lots = list(lot_data.values())

                if not lots and default_src:
                    quants = quant_model.search(
                        [
                            ("product_id", "=", prod.id),
                            ("location_id", "child_of", default_src.id),
                            ("lot_id", "!=", False),
                            ("quantity", ">", 0),
                        ],
                        order="in_date asc",
                        limit=40,
                    )
                    seen_lots = set()
                    for q in quants:
                        if q.lot_id.id in seen_lots:
                            continue
                        seen_lots.add(q.lot_id.id)
                        lots.append(
                            {
                                "id": q.lot_id.id,
                                "name": q.lot_id.display_name,
                                "location_id": q.location_id.id,
                                "quantity": q.quantity,
                            }
                        )

            product_lots_map[p["id"]] = lots

        products_payload = []
        for p in unique_products:
            payload = dict(p, lots=product_lots_map.get(p["id"], []))
            if p.get("type") == "finished" and finished_lot:
                payload.update(
                    {
                        "default_lot_id": finished_lot.id,
                        "default_lot_name": finished_lot.display_name,
                    }
                )
            products_payload.append(payload)

        # Default source location detection logic
        # For FG: MO destination or Picking Type default
        # For Components: MO source or Picking Type default
        default_fg_src = (
            production.location_dest_id
            or production.picking_type_id.default_location_dest_id
        )
        default_comp_src = (
            production.location_src_id
            or production.picking_type_id.default_location_src_id
        )

        return {
            "products": products_payload,
            "locations": [
                {"id": loc.id, "name": loc.display_name} for loc in internal_locs
            ],
            "scrap_locations": [
                {"id": loc.id, "name": loc.display_name} for loc in scrap_locs
            ],
            "default_location_id": default_fg_src.id
            if default_fg_src
            else (default_comp_src.id if default_comp_src else False),
            "default_scrap_location_id": scrap_locs[:1].id if scrap_locs else False,
            "scrap_reasons": [
                {"id": tag.id, "name": tag.display_name}
                for tag in request.env["stock.scrap.reason.tag"].search([], limit=80)
            ]
            if "stock.scrap.reason.tag" in request.env.registry
            else [],
        }

    @http.route("/mrp_parallel_console/create_scrap", type="json", auth="user")
    def create_scrap(
        self,
        workorder_id,
        product_id,
        quantity,
        location_id=None,
        scrap_location_id=None,
        reason=None,
        scrap_reason_tag_ids=None,
        lot_id=None,
        lot_name=None,
        workcenter_name=None,
    ):
        _require_group("mrp.group_mrp_user")
        workorder = request.env[MRP_WORKORDER_MODEL].browse(workorder_id)
        if not workorder.exists():
            return {"error": WORKORDER_NOT_FOUND}
        if not product_id:
            return {"error": "Product is required for scrap."}

        production = workorder.production_id
        scrap_model = request.env["stock.scrap"]
        # Guard: cap scrap quantity for components at required quantity
        # Component quantity guard
        raw_move = production.move_raw_ids.filtered(
            lambda m: m.product_id.id == product_id
        )[:1]
        if (
            raw_move
            and float_compare(
                quantity,
                raw_move.product_uom_qty,
                precision_rounding=raw_move.product_uom.rounding or 0.000001,
            )
            > 0
        ):
            return {
                "error": _(
                    "Scrap quantity cannot exceed required component quantity (%s)"
                )
                % raw_move.product_uom_qty
            }
        # Finished product quantity guard
        if product_id == production.product_id.id:
            if (
                float_compare(
                    quantity,
                    production.product_qty,
                    precision_rounding=production.product_uom_id.rounding or 0.000001,
                )
                > 0
            ):
                return {
                    "error": _(
                        "Scrap quantity cannot exceed finished product planned quantity (%s)"
                    )
                    % production.product_qty
                }

        product = request.env["product.product"].browse(product_id)
        vals = {
            "product_id": product_id,
            "product_uom_id": product.uom_id.id if product else False,
            "scrap_qty": quantity,
            "company_id": production.company_id.id,
            "origin": workcenter_name or production.name,
            "production_id": production.id,
            "workorder_id": workorder.id,
            "state": "draft",
        }
        if location_id:
            vals["location_id"] = location_id
        if scrap_location_id:
            vals["scrap_location_id"] = scrap_location_id
        if reason:
            if "note" in scrap_model._fields:
                vals["note"] = reason
            elif "description" in scrap_model._fields:
                vals["description"] = reason

        # Handle tags
        if scrap_reason_tag_ids and "scrap_reason_tag_ids" in scrap_model._fields:
            # Ensure it's a list of IDs
            if isinstance(scrap_reason_tag_ids, (int, str)):
                scrap_reason_tag_ids = [int(scrap_reason_tag_ids)]
            vals["scrap_reason_tag_ids"] = [(6, 0, scrap_reason_tag_ids)]

        if product_id == production.product_id.id:
            source_loc = (
                production.location_dest_id
                or production.picking_type_id.default_location_dest_id
            )
        else:
            source_loc = (
                production.location_src_id
                or production.picking_type_id.default_location_src_id
            )

        if not vals.get("location_id") and source_loc:
            vals["location_id"] = source_loc.id

        if lot_id and "lot_id" in scrap_model._fields:
            vals["lot_id"] = lot_id
        elif product_id == production.product_id.id and production.lot_producing_id:
            vals["lot_id"] = production.lot_producing_id.id
        elif lot_name and "lot_name" in scrap_model._fields:
            vals["lot_name"] = lot_name

        scrap_loc = False
        if scrap_location_id:
            scrap_loc = request.env["stock.location"].browse(scrap_location_id)

        if not scrap_loc or not scrap_loc.exists():
            if product_id == production.product_id.id:
                scrap_loc = production.location_dest_id or getattr(
                    production.picking_type_id, "default_location_dest_id", False
                )

        if not scrap_loc:
            scrap_loc = request.env["stock.location"].search(
                [("scrap_location", "=", True)], limit=1
            )

        if scrap_loc:
            vals["scrap_location_id"] = scrap_loc.id

        scrap = scrap_model.create(vals)

        # Integration: Mrp Scrap Landed Cost
        if "mrp.scrap.record" in request.env:
            try:
                scrap_type = (
                    "fg" if product_id == production.product_id.id else "component"
                )
                unit_cost = product.standard_price or 0.0
                total_cost = quantity * unit_cost
                request.env["mrp.scrap.record"].create(
                    {
                        "mo_id": production.id,
                        "product_id": product_id,
                        "scrap_type": scrap_type,
                        "qty": quantity,
                        "cost": total_cost,
                        "company_id": production.company_id.id,
                        "scrap_id": scrap.id,
                    }
                )
            except Exception:
                # Shield console from integration failures to ensure scrap remains reliable
                pass

        if reason:
            try:
                scrap.message_post(
                    body=reason,
                    message_type="comment",
                    subtype_xmlid="mail.mt_note",
                )
            except Exception:
                pass
        try:
            production.message_post(
                body=_("Scrap created on console (draft): %s %s. Reason: %s")
                % (
                    quantity,
                    scrap.product_uom_name
                    if hasattr(scrap, "product_uom_name")
                    else "",
                    reason or "",
                )
            )
        except Exception:
            pass
        return {
            "status": "success",
            "scrap_id": scrap.id,
            "scrap_name": scrap.name,
            "message": _("Scrap recorded (Draft)."),
        }

    # ---------------------------------------------------------
    # Start / Stop from console (server timestamp)
    # ---------------------------------------------------------
    def _component_reservation_diagnostic(self, move):
        product = move.product_id
        source_location = move.location_id or move.raw_material_production_id.location_src_id
        rounding = move.product_uom.rounding or 0.000001
        demand_qty = move.product_uom_qty or 0.0
        reserved_qty = move.quantity or 0.0
        shortage_qty = max(demand_qty - reserved_qty, 0.0)

        Quant = request.env[STOCK_QUANT_MODEL].sudo()
        lot = move.move_line_ids.mapped('lot_id')[:1]
        physical_free_qty_product_uom = Quant._get_available_quantity(
            product,
            source_location,
            lot_id=lot if lot else None,
            strict=False,
        )
        try:
            usable_free_qty_product_uom = move._get_available_quantity(
                source_location,
                lot_id=lot if lot else None,
                strict=False,
            )
        except Exception:
            usable_free_qty_product_uom = physical_free_qty_product_uom

        physical_free_qty_move_uom = product.uom_id._compute_quantity(
            physical_free_qty_product_uom,
            move.product_uom,
        )
        usable_free_qty_move_uom = product.uom_id._compute_quantity(
            usable_free_qty_product_uom,
            move.product_uom,
        )
        on_hand_qty_product_uom = product.with_context(
            location=source_location.id,
        ).qty_available

        quant_domain = [
            ('product_id', '=', product.id),
            ('location_id', 'child_of', source_location.id),
        ]
        if lot:
            quant_domain.append(('lot_id', '=', lot.id))
        quants = Quant.search(quant_domain)
        reserved_quant_qty = product.uom_id._compute_quantity(
            sum(quants.mapped('reserved_quantity')),
            move.product_uom,
        )
        lot_names = ', '.join(quants.mapped('lot_id.name')[:5]) or '-'
        lot_expirations = []
        for quant in quants.filtered(lambda q: q.lot_id)[:5]:
            lot_date = (
                getattr(quant.lot_id, 'expiration_date', False)
                or getattr(quant.lot_id, 'removal_date', False)
                or '-'
            )
            lot_expirations.append("%s:%s" % (quant.lot_id.name, lot_date))
        lot_expiration_names = ', '.join(lot_expirations) or '-'
        owner_names = ', '.join(quants.mapped('owner_id.display_name')[:5]) or '-'
        package_names = ', '.join(quants.mapped('package_id.name')[:5]) or '-'
        use_expiration = bool(
            getattr(product, 'use_expiration_date', False)
            or getattr(product.product_tmpl_id, 'use_expiration_date', False)
        )

        if move.procure_method == 'make_to_order' and move.move_orig_ids:
            reason = _("Waiting for upstream supply before this component can be reserved.")
        elif float_compare(on_hand_qty_product_uom, 0.0, precision_rounding=product.uom_id.rounding or rounding) <= 0:
            reason = _("No on-hand stock in the MO source location.")
        elif (
            use_expiration
            and float_compare(physical_free_qty_move_uom, shortage_qty, precision_rounding=rounding) >= 0
            and float_compare(usable_free_qty_move_uom, shortage_qty, precision_rounding=rounding) < 0
        ):
            reason = _("Stock exists, but available lots are expired or not usable for the required date.")
        elif float_compare(usable_free_qty_move_uom, shortage_qty, precision_rounding=rounding) < 0:
            reason = _("On-hand stock exists, but free quantity is not enough after existing reservations.")
        elif product.tracking != 'none' and not move.move_line_ids.mapped('lot_id'):
            reason = _("Tracked product: reservation may require a matching lot/serial.")
        else:
            reason = _("Free stock exists, but Odoo could not reserve it. Check lot, package, owner, removal strategy, or rounding.")

        message = _(
            "%(product)s | Source: %(source)s | Demand: %(demand).6g %(uom)s | "
            "Reserved on MO: %(reserved).6g %(uom)s | Usable Free: %(usable_free).6g %(uom)s | "
            "Physical Free: %(physical_free).6g %(uom)s | "
            "Reserved by quants: %(quant_reserved).6g %(uom)s | Route method: %(procure)s | "
            "Tracking: %(tracking)s | Lots: %(lots)s | Lot Dates: %(lot_dates)s | "
            "Owner: %(owners)s | Package: %(packages)s | "
            "Reason: %(reason)s"
        ) % {
            'product': product.display_name,
            'source': source_location.display_name,
            'demand': demand_qty,
            'reserved': reserved_qty,
            'usable_free': usable_free_qty_move_uom,
            'physical_free': physical_free_qty_move_uom,
            'quant_reserved': reserved_quant_qty,
            'uom': move.product_uom.name,
            'procure': move.procure_method,
            'tracking': product.tracking,
            'lots': lot_names,
            'lot_dates': lot_expiration_names,
            'owners': owner_names,
            'packages': package_names,
            'reason': reason,
        }
        return {
            'product_id': product.id,
            'product_name': product.display_name,
            'source_location_id': source_location.id,
            'source_location_name': source_location.display_name,
            'demand_qty': demand_qty,
            'reserved_qty': reserved_qty,
            'free_qty': usable_free_qty_move_uom,
            'usable_free_qty': usable_free_qty_move_uom,
            'physical_free_qty': physical_free_qty_move_uom,
            'reserved_quant_qty': reserved_quant_qty,
            'uom': move.product_uom.name,
            'procure_method': move.procure_method,
            'tracking': product.tracking,
            'lots': lot_names,
            'lot_dates': lot_expiration_names,
            'owners': owner_names,
            'packages': package_names,
            'reason': reason,
            'message': message,
        }

    @http.route("/mrp_parallel_console/check_components", type="json", auth="user")
    def check_components(self, workorder_id):
        """Check if all components are available before starting workorder."""
        _require_group("mrp.group_mrp_user")
        workorder = request.env[MRP_WORKORDER_MODEL].browse(workorder_id)
        if not workorder.exists():
            return {"error": WORKORDER_NOT_FOUND}

        production = workorder.production_id
        if not production:
            return {"error": "No production order linked."}

        # Check component availability
        # If we have unreserved moves but stock is available, try to reserve it (Auto-fix for backorders/rounding issues)
        if production.state in ("confirmed", "progress", "to_close"):
            needs_reserve = False
            for move in production.move_raw_ids.filtered(
                lambda m: m.state not in ("done", "cancel")
            ):
                if (
                    float_compare(
                        move.quantity,
                        move.product_uom_qty,
                        precision_rounding=move.product_uom.rounding,
                    )
                    < 0
                ):
                    needs_reserve = True
                    break
            if needs_reserve:
                production.move_raw_ids.filtered(
                    lambda m: m.state not in ("done", "cancel")
                )._action_assign()

        missing_components = []
        diagnostics = []
        for move in production.move_raw_ids.filtered(
            lambda m: m.state not in ("done", "cancel")
        ):
            if (
                float_compare(
                    move.quantity,
                    move.product_uom_qty,
                    precision_rounding=move.product_uom.rounding or 0.000001,
                )
                < 0
            ):
                missing_components.append(move.product_id.display_name)
                diagnostics.append(self._component_reservation_diagnostic(move))

        if missing_components:
            diagnostic_messages = "\n".join(item["message"] for item in diagnostics[:5])
            return {
                "sufficient": False,
                "missing_components": missing_components,
                "diagnostics": diagnostics,
                "error": _(
                    "Some components could not be reserved:\n%s"
                ) % diagnostic_messages,
            }

        return {"sufficient": True}

    @http.route("/mrp_parallel_console/start_workorder", type="json", auth="user")
    def start_workorder(self, workorder_id, allow_full_mold=False):
        _require_group("mrp.group_mrp_user")
        workorder = request.env[MRP_WORKORDER_MODEL].browse(workorder_id)
        if not workorder.exists():
            return {"error": WORKORDER_NOT_FOUND}

        allow_full_mold = str(allow_full_mold).strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )

        # Mold Capacity Check
        if hasattr(workorder, "mold_ids") and workorder.mold_ids and not allow_full_mold:
            full_molds = workorder.mold_ids.filtered(
                lambda mold: getattr(mold, "mold_state", "normal") == "full"
            )
            if full_molds:
                alternatives = self._mpc_get_alternative_mold_lines(
                    workorder,
                    exclude_mold_ids=workorder.mold_ids.ids,
                    exclude_full=True,
                )
                if not alternatives:
                    alternatives = self._mpc_get_alternative_mold_lines(
                        workorder,
                        exclude_mold_ids=workorder.mold_ids.ids,
                        exclude_full=False,
                    )
                return {
                    "status": "mold_warning",
                    "message": _(
                        "The following molds have reached their shot limit: %s."
                    )
                    % ", ".join(full_molds.mapped("name")),
                    "molds": self._mpc_get_workorder_mold_payload(workorder),
                    "alternatives": alternatives,
                    "action": self._mpc_get_mold_selection_action(workorder),
                }

        if (
            self._mpc_enforce_employee_breakdown()
            and workorder.workcenter_id.mpc_require_employee_production
            and not workorder.employee_ids
        ):
            return {
                "error": _(
                    "Please assign at least one employee before starting this workorder."
                )
            }

        # Guard: block start when workcenter is under maintenance or busy with another WO.
        wc = workorder.workcenter_id
        # Maintenance state on workcenter
        if getattr(wc, "maintenance_state", False) == "maintenance":
            return {"error": _("Workcenter %s is under maintenance.") % wc.display_name}

        # Maintenance requests not done/cancel
        if "maintenance.request" in request.env.registry:
            MaintReq = request.env["maintenance.request"]
            domain = [("workcenter_id", "=", wc.id)]
            if "state" in MaintReq._fields:
                domain.append(("state", "not in", ["done", "cancel"]))
            elif "stage_id" in MaintReq._fields:
                stage_field = MaintReq._fields.get("stage_id")
                stage_model = getattr(stage_field, "comodel_name", False)
                if stage_model and "done" in request.env[stage_model]._fields:
                    domain.append(("stage_id.done", "=", False))
            if "maintenance_type" in MaintReq._fields:
                domain.append(("maintenance_type", "in", ["corrective", "preventive"]))
            if MaintReq.search_count(domain):
                return {
                    "error": _("Workcenter %s is under maintenance request.")
                    % wc.display_name
                }

        # Busy: other workorders in progress on same workcenter
        other_progress = request.env[MRP_WORKORDER_MODEL].search_count(
            [
                ("workcenter_id", "=", wc.id),
                ("state", "=", "progress"),
                ("id", "!=", workorder.id),
            ]
        )
        if other_progress:
            return {
                "error": _("Workcenter %s is busy with another workorder.")
                % wc.display_name
            }

        check_method = getattr(
            workorder, "_check_single_job_per_workcenter_before_start", None
        )
        if check_method:
            check_method()

        production = workorder.production_id
        component_warning = False
        if production and production.state in ("confirmed", "progress", "to_close"):
            unreserved = production.move_raw_ids.filtered(
                lambda m: m.state not in ("done", "cancel")
                and float_compare(
                    m.quantity,
                    m.product_uom_qty,
                    precision_rounding=m.product_uom.rounding or 0.000001,
                )
                < 0
            )
            if unreserved:
                try:
                    unreserved._action_assign()
                except Exception:
                    pass
                still_missing = unreserved.filtered(
                    lambda m: float_compare(
                        m.quantity,
                        m.product_uom_qty,
                        precision_rounding=m.product_uom.rounding or 0.000001,
                    )
                    < 0
                )
                if still_missing:
                    component_warning = True

        workorder.action_console_start_timer()
        result = {
            "status": "ok",
            "start": fields.Datetime.to_string(workorder.console_date_start),
            "state": workorder.state,
        }
        if component_warning:
            result["component_warning"] = True
        return result

    @http.route(
        "/mrp_parallel_console/get_mold_selection_action", type="json", auth="user"
    )
    def get_mold_selection_action(self, workorder_id):
        _require_group("mrp.group_mrp_user")
        workorder = request.env[MRP_WORKORDER_MODEL].browse(workorder_id)
        if not workorder.exists():
            return {"error": WORKORDER_NOT_FOUND}
        return {"action": self._mpc_get_mold_selection_action(workorder)}

    @http.route("/mrp_parallel_console/stop_workorder", type="json", auth="user")
    def stop_workorder(self, workorder_id):
        _require_group("mrp.group_mrp_user")
        workorder = request.env[MRP_WORKORDER_MODEL].browse(workorder_id)
        if not workorder.exists():
            return {"error": WORKORDER_NOT_FOUND}

        workorder.action_console_stop_timer()
        return {
            "status": "ok",
            "end": fields.Datetime.to_string(workorder.console_date_finished),
            "state": workorder.state,
        }

    @http.route("/mrp_parallel_console/finish_workorder", type="json", auth="user")
    def finish_workorder(self, workorder_id):
        _require_group("mrp.group_mrp_user")
        workorder = request.env[MRP_WORKORDER_MODEL].browse(workorder_id)
        if not workorder.exists():
            return {"error": WORKORDER_NOT_FOUND}

        try:
            state, end = self._finish_single_workorder(workorder)
            return {
                "status": "ok",
                "state": state,
                "end": end,
            }
        except UserError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"Failed to finish workorder: {str(e)}"}

    def _finish_single_workorder(self, workorder):
        """Mark a single workorder as finished, returning (state, end_datetime_str)."""
        if workorder.state == "cancel":
            return workorder.state, fields.Datetime.to_string(workorder.console_date_finished or fields.Datetime.now())

        # --- Strict Validation ---
        # Sync field with logs before validation to ensure consistency
        done_qty = self._get_effective_console_qty(workorder)
        workorder.console_qty = done_qty

        total_emp_qty = sum(workorder.mpc_employee_production_ids.mapped("qty"))

        # 1. Always enforce non-zero quantity in console
        if done_qty <= 0:
            raise UserError(
                _("%s: You must report a production quantity (Done > 0) before finishing.")
                % workorder.workcenter_id.name
            )

        # 2. Enforce breakdown if required (and enabled)
        if self._mpc_enforce_employee_breakdown():
            if workorder.workcenter_id.mpc_require_employee_production:
                if not workorder.mpc_employee_production_ids:
                    raise UserError(
                        _("%s: You must provide an employee production breakdown.")
                        % workorder.workcenter_id.name
                    )
                if abs(total_emp_qty - done_qty) > 0.0001:
                    raise UserError(
                        _("%s: Total breakdown quantity (%s) must match the 'Done' quantity (%s).")
                        % (workorder.workcenter_id.name, total_emp_qty, done_qty)
                    )

        if workorder.console_date_start and not workorder.console_date_finished:
            workorder.action_console_stop_timer()

        production = workorder.production_id
        rounding = production.product_uom_id.rounding or 0.000001
        total_qty = production._console_compute_total_qty(
            production.workorder_ids, mode="progress"
        )
        if float_compare(total_qty, production.product_qty, precision_rounding=rounding) > 0:
            production._console_sync_demand_and_replenish(total_qty)
        if float_compare(
            production.qty_producing or 0.0,
            total_qty,
            precision_rounding=rounding,
        ) != 0:
            production.qty_producing = total_qty
        production._console_fill_auto_component_moves(total_qty)

        workorder.with_context(mpc_skip_quality_checks=True).button_finish()
        end = fields.Datetime.to_string(
            workorder.console_date_finished or fields.Datetime.now()
        )
        return workorder.state, end

    @http.route("/mrp_parallel_console/quick_done", type="json", auth="user")
    def quick_done(self, workorder_id, qty):
        _require_group("mrp.group_mrp_user")
        try:
            qty = float(qty or 0.0)
        except (TypeError, ValueError):
            return {"error": _("Invalid production quantity.")}
        if qty <= 0:
            return {"error": _("Production quantity must be greater than zero.")}

        workorder = request.env[MRP_WORKORDER_MODEL].browse(workorder_id)
        if not workorder.exists():
            return {"error": WORKORDER_NOT_FOUND}
        if workorder.state == "cancel":
            return {"error": _("Cancelled workorders cannot be finished from the console.")}

        if workorder.production_id.state not in (
            "confirmed",
            "progress",
            "to_close",
        ):
            return {"error": _("Manufacturing order is not open for production.")}

        wc = workorder.workcenter_id
        if getattr(wc, "maintenance_state", False) == "maintenance":
            return {"error": _("Workcenter %s is under maintenance.") % wc.display_name}

        if (
            self._mpc_enforce_employee_breakdown()
            and wc.mpc_require_employee_production
            and not workorder.employee_ids
        ):
            return {
                "error": _(
                    "Please assign at least one employee before starting this workorder."
                )
            }

        done_qty = workorder.console_qty or 0.0

        if workorder.state in ("ready", "waiting", "pending"):
            workorder.action_console_start_timer()

        workorder.console_qty = (workorder.console_qty or 0.0) + qty

        production = workorder.production_id
        rounding = production.product_uom_id.rounding or 0.000001
        total_qty = done_qty + qty
        if float_compare(total_qty, production.product_qty, precision_rounding=rounding) > 0:
            production._console_sync_demand_and_replenish(total_qty)
        if float_compare(
            production.qty_producing or 0.0,
            total_qty,
            precision_rounding=rounding,
        ) != 0:
            production.qty_producing = total_qty
        production._console_fill_auto_component_moves(total_qty)

        if workorder.console_date_start and not workorder.console_date_finished:
            workorder.action_console_stop_timer()

        workorder.with_context(mpc_skip_quality_checks=True).button_finish()

        return {
            "status": "ok",
            "start": fields.Datetime.to_string(workorder.console_date_start),
            "end": fields.Datetime.to_string(workorder.console_date_finished or fields.Datetime.now()),
            "state": workorder.state,
        }

    # ---------------------------------------------------------
    # Quality check tools
    # ---------------------------------------------------------
    @http.route("/mrp_parallel_console/create_quality_check", type="json", auth="user")
    def create_quality_check(self, workorder_id, note=None, result="pass"):
        _require_group("mrp.group_mrp_user")
        workorder = request.env[MRP_WORKORDER_MODEL].browse(workorder_id)
        if not workorder.exists():
            return {"error": WORKORDER_NOT_FOUND}

        qc, error_msg, warning = self._mpc_prepare_workorder_quality_check(workorder)
        if error_msg:
            return {"error": error_msg}
        if not qc:
            return {
                "status": "ok",
                "action": False,
                "warning": warning
                or _("No quality control points found for this work order operation."),
            }

        return {"status": "ok", "action": self._mpc_quality_action(qc)}

    def _mpc_quality_action(self, check):
        return {
            "name": _("Quality Check"),
            "type": "ir.actions.act_window",
            "res_model": "quality.check",
            "view_mode": "form",
            "target": "new",
            "res_id": check.id,
            "views": [(False, "form")],
        }

    def _mpc_prepare_workorder_quality_check(self, workorder):
        """Ensure a quality check exists for the given workorder.

        :returns: tuple (quality.check record or False, error_message, warning_message)
        """
        registry = request.env.registry
        if "quality.check" not in registry or "quality.point" not in registry:
            return (
                False,
                _(
                    "Quality module is not fully installed. Please install Quality Control and Work Order Quality modules."
                ),
                False,
            )

        QualityPoint = request.env["quality.point"]
        QualityCheck = request.env["quality.check"]

        domain = [("operation_id", "=", workorder.operation_id.id)]
        if "picking_type_id" in QualityPoint._fields:
            domain.append(("picking_type_id", "=", False))
        if "team_id" in QualityPoint._fields:
            domain.append(("team_id", "!=", False))

        point = QualityPoint.search(domain, limit=1)
        if not point:
            return (False, False, False)

        check = QualityCheck.search(
            [
                ("workorder_id", "=", workorder.id),
                ("point_id", "=", point.id),
            ],
            limit=1,
        )
        if not check:
            vals = {
                "point_id": point.id,
                "workorder_id": workorder.id,
                "production_id": workorder.production_id.id,
                "team_id": point.team_id.id,
                "company_id": workorder.company_id.id,
                "product_id": workorder.product_id.id,
                "picking_id": False,
                "lot_id": workorder.finished_lot_id.id
                if workorder.finished_lot_id
                else False,
            }
            check = QualityCheck.create(vals)
        return (check, False, False)

    def _mpc_get_pending_quality_action(self, productions, workorders):
        """Return an action to open the next pending quality check if any."""
        registry = request.env.registry
        if "quality.check" not in registry:
            return False

        QualityCheck = request.env["quality.check"]
        workorders = workorders.sorted("id") if workorders else workorders

        for wo in workorders or []:
            pending = QualityCheck.search(
                [
                    ("workorder_id", "=", wo.id),
                    ("quality_state", "not in", ["pass", "fail"]),
                ],
                order="id",
                limit=1,
            )
            if not pending:
                pending, _, _ = self._mpc_prepare_workorder_quality_check(wo)
            if pending and pending.quality_state not in ("pass", "fail"):
                return self._mpc_quality_action(pending)

        for mo in productions:
            pending = QualityCheck.search(
                [
                    ("production_id", "=", mo.id),
                    ("workorder_id", "=", False),
                    ("quality_state", "not in", ["pass", "fail"]),
                ],
                order="id",
                limit=1,
            )
            if pending:
                return self._mpc_quality_action(pending)
        return False

    # ---------------------------------------------------------
    # Confirm MO from dashboard card
    # ---------------------------------------------------------
    @http.route("/mrp_parallel_console/confirm_mo", type="json", auth="user")
    def confirm_mo(self, production_id):
        _require_group("mrp.group_mrp_user")
        production = request.env[MRP_PRODUCTION_MODEL].browse(production_id)
        if not production.exists():
            return {"error": "Manufacturing order not found."}

        action = False
        if hasattr(production, "action_confirm"):
            action = production.with_context(show_mold_bom_wizard=True).action_confirm()
        elif hasattr(production, "button_confirm"):
            action = production.button_confirm()
        else:
            return {"error": "No confirm method on mrp.production."}

        if action and isinstance(action, dict):
            return {"status": "action", "action": action}
        return {"status": "ok"}

    @http.route("/mrp_parallel_console/manual_close_mo", type="json", auth="user")
    def manual_close_mo(self, production_id):
        _require_group("mrp.group_mrp_user")
        production = request.env[MRP_PRODUCTION_MODEL].browse(production_id)
        if not production.exists():
            return {"error": "Manufacturing order not found."}

        if (
            production.product_tracking in ("lot", "serial")
            and not production.lot_producing_id
            and not production.workorder_ids.filtered("finished_lot_id")
        ):
            return {
                "status": "lot_required",
                "action": self._console_get_assign_lot_action(production),
            }

        # Auto mark standard consumption/production before closing so the
        # backend wizard does not stop on Consumption Warning.
        production._console_fill_move_quantities_for_close()

        # ---------- Enforce QC per WO before closing ----------
        registry = request.env.registry
        company = production.company_id
        # If quality modules are not installed, skip QC enforcement entirely
        if (
            company.mpc_qc_block_close
            and "quality.check" in registry
            and "quality.point" in registry
        ):
            quality_check_model = request.env["quality.check"]
            quality_point_model = request.env["quality.point"]

            pending_wos = []
            for wo in production.workorder_ids:
                if wo.state == "cancel":
                    continue

                # If there is no QC Point linked to this operation, do not enforce QC
                has_point = quality_point_model.search(
                    [("operation_id", "=", wo.operation_id.id)],
                    limit=1,
                )
                if not has_point:
                    continue

                done_checks = quality_check_model.search(
                    [
                        ("workorder_id", "=", wo.id),
                        ("quality_state", "in", ["pass", "fail"]),
                    ],
                    limit=1,
                )
                if not done_checks:
                    pending_wos.append(wo)

            if pending_wos:
                names = ", ".join(pending_wos.mapped("name"))
                raise UserError(
                    _(
                        "You must complete the quality checks for all work orders "
                        "before closing this manufacturing order.\n\nPending WOs: %s"
                    )
                    % names
                )


        action = production.with_context(skip_backorder=False).button_mark_done()
        return {"status": "ok", "action": action}

    def _console_get_assign_lot_action(self, production):
        """Return action to open Assign LOT wizard before closing."""
        return {
            "type": "ir.actions.act_window",
            "name": _("Assign LOT"),
            "res_model": "mrp.parallel.assign.lot.wizard",
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "new",
            "context": {
                "default_production_id": production.id,
                "active_id": production.id,
                "active_model": production._name,
            },
        }

    # ---------------------------------------------------------
    # Maintenance Integration
    # ---------------------------------------------------------
    @http.route(
        "/mrp_parallel_console/action_maintenance_request", type="json", auth="user"
    )
    def action_maintenance_request(self, workorder_id):
        _require_group("mrp.group_mrp_user")
        wo = request.env[MRP_WORKORDER_MODEL].browse(workorder_id)
        if not wo.exists():
            return {"error": WORKORDER_NOT_FOUND}

        equipment = (
            wo.workcenter_id.equipment_ids[:1]
            if hasattr(wo.workcenter_id, "equipment_ids")
            else request.env["maintenance.equipment"]
        )
        team = (
            wo.workcenter_id.maintenance_team_id
            if hasattr(wo.workcenter_id, "maintenance_team_id")
            else False
        )

        return {
            "status": "ok",
            "action": {
                "type": "ir.actions.act_window",
                "name": _("Maintenance Request"),
                "res_model": "maintenance.request",
                "view_mode": "form",
                "views": [[False, "form"]],
                "target": "new",
                "context": {
                    "default_name": _("Maintenance for %s") % wo.workcenter_id.name,
                    "default_workcenter_id": wo.workcenter_id.id,
                    "default_production_id": wo.production_id.id,
                    "default_equipment_id": equipment.id if equipment else False,
                    "default_maintenance_team_id": team.id if team else False,
                },
            },
        }

    # ---------------------------------------------------------
    # Component picking helpers (embedded mini picking UI)
    # ---------------------------------------------------------

    @http.route("/mrp_parallel_console/get_picking", type="json", auth="user")
    def get_picking(self, production_id=None, picking_id=None):
        _require_group("stock.group_stock_user")
        picking_model = request.env[STOCK_PICKING_MODEL]
        production_model = request.env[MRP_PRODUCTION_MODEL]

        production = False
        selected_picking = False
        if picking_id:
            selected_picking = picking_model.browse(picking_id)
            if selected_picking.exists():
                production = selected_picking.production_id
            else:
                selected_picking = False

        if not production and production_id:
            production = production_model.browse(production_id)

        if not production or not production.exists():
            return {"error": "No pending component picking found for this MO."}

        pending_pickings = self._console_pending_pickings(production)
        if not pending_pickings:
            # Attempt to reserve stock if no pickings are found (handle Backorder/Late reservation cases)
            if production.state in ("confirmed", "progress", "to_close"):
                production.action_assign()
                pending_pickings = self._console_pending_pickings(production)

        if not pending_pickings:
            return {"error": "No pending component picking found for this MO."}

        if selected_picking and selected_picking in pending_pickings:
            picking = selected_picking
        else:
            picking = self._console_choose_picking(pending_pickings)

        if not picking:
            return {"error": "No pending component picking found for this MO."}

        if picking.state not in ("done", "cancel"):
            try:
                picking.action_assign()
            except Exception:
                # Ignore assign errors; UI will still allow manual entry
                pass

        return {
            "picking": self._serialize_picking(picking),
            "available_pickings": [
                self._serialize_picking_option(option)
                for option in self._console_sort_pickings(pending_pickings)
            ],
        }

    @http.route("/mrp_parallel_console/validate_picking", type="json", auth="user")
    def validate_picking(self, picking_id, moves):
        _require_group("stock.group_stock_user")
        picking = request.env[STOCK_PICKING_MODEL].browse(picking_id)
        if not picking.exists():
            return {"error": "Picking not found."}

        production = self._console_get_picking_production(picking)
        if not production:
            return {"error": _("Picking is not linked to a manufacturing order.")}

        if picking.state == "done":
            return {"error": "Picking already validated."}

        picking.action_assign()

        lines_payload, missing_moves = self._prepare_move_lines_for_validation(
            picking, moves
        )
        if missing_moves:
            return {
                "error": _(
                    "Some component lines were refreshed. Please reload and try again."
                )
            }
        for move, new_lines in lines_payload.items():
            if not new_lines:
                continue
            for vals in new_lines:
                matched_line = False
                rounding = move.product_uom.rounding or 0.000001
                target_qty = float_round(vals.get("quantity", 0.0), precision_rounding=rounding)
                for line in move.move_line_ids:
                    if line.lot_id.id == vals.get(
                        "lot_id"
                    ) and line.location_id.id == vals.get("location_id"):
                        if "quantity" in line._fields:
                            line.quantity = target_qty
                        else:
                            line.qty_done = target_qty
                        matched_line = True
                        break
                if not matched_line:
                    move.move_line_ids.create(vals)



        action = picking.with_context(
            skip_immediate=True, skip_backorder=True
        ).button_validate()

        # Immediately sync quantities to the MO consumption
        if production:
            production.sudo().action_sync_picked_quantities()

        pending_count = 0
        production = production or getattr(picking, "production_id", False)
        if production:
            pending_count = len(self._console_pending_pickings(production))
        return {
            "status": "ok",
            "picking": self._serialize_picking(picking),
            "action": action,
            "pending_pickings_count": pending_count,
        }

    def _prepare_move_lines_for_validation(self, picking, moves):
        move_model = request.env[STOCK_MOVE_MODEL]
        lot_model = request.env[STOCK_LOT_MODEL]
        payload = {}
        missing_moves = set()
        for move_data in moves or []:
            move_id = move_data.get("move_id")
            if not move_id:
                continue
            move = move_model.browse(move_id)
            if not move.exists():
                missing_moves.add(move_id)
                continue
            if move.picking_id != picking:
                continue
            vals_list = self._build_move_line_vals(
                move,
                picking,
                move_data.get("lines", []),
                lot_model,
            )
            if not vals_list:
                if move.product_id.tracking in ("lot", "serial"):
                    raise UserError("Please set lot/serial numbers before validating.")
                rounding = move.product_uom.rounding or 0.000001

                qty = float_round(move.product_uom_qty, precision_rounding=rounding)
                vals_list = [
                    {
                        "move_id": move.id,
                        "picking_id": picking.id,
                        "company_id": picking.company_id.id,
                        "product_id": move.product_id.id,
                        "product_uom_id": move.product_uom.id,
                        "quantity": qty,
                        "location_id": picking.location_id.id,
                        "location_dest_id": picking.location_dest_id.id,
                    }
                ]
            self._validate_move_line_stock(move, vals_list)
            payload[move] = vals_list
        return payload, missing_moves

    def _build_move_line_vals(self, move, picking, line_payloads, lot_model):
        rounding = move.product_uom.rounding or 0.000001

        vals_list = []
        for line in line_payloads:
            qty = float(line.get("qty_done") or 0)
            qty = float_round(qty, precision_rounding=rounding)
            if qty <= 0:
                continue
            lot_id = self._resolve_lot_for_move(
                move, picking, line.get("lot_id"), line.get("lot_name"), lot_model
            )
            line_location = line.get("location_id")
            if line_location:
                try:
                    location_id = int(line_location)
                except (TypeError, ValueError):
                    location_id = False
            else:
                location_id = False
            if not location_id:
                location_id = picking.location_id.id
            vals = {
                "move_id": move.id,
                "picking_id": picking.id,
                "company_id": picking.company_id.id,
                "product_id": move.product_id.id,
                "product_uom_id": move.product_uom.id,
                "quantity": qty,  # Changed from qty_done to quantity
                "location_id": location_id,
                "location_dest_id": picking.location_dest_id.id,
            }
            if lot_id:
                vals["lot_id"] = lot_id
            vals_list.append(vals)
        return vals_list

    def _validate_move_line_stock(self, move, vals_list):
        """Ensure each selected location has sufficient available stock."""
        if not vals_list:
            return
        quant_model = request.env[STOCK_QUANT_MODEL]
        lot_model = request.env[STOCK_LOT_MODEL]
        location_model = request.env["stock.location"]
        precision = move.product_uom.rounding or 0.000001
        required = defaultdict(float)

        for vals in vals_list:
            location_id = vals.get("location_id")
            qty = float(vals.get("quantity") or 0.0)
            if not location_id or qty <= 0:
                continue
            lot_id = vals.get("lot_id") or False
            required[(location_id, lot_id)] += qty

        for (location_id, lot_id), needed_qty in required.items():
            if needed_qty <= 0:
                continue
            location = location_model.browse(location_id)
            if not location.exists():
                raise UserError(
                    _(
                        "Selected location no longer exists. Please reload and try again."
                    )
                )
            lot = lot_id and lot_model.browse(lot_id) or False
            available_product_uom = quant_model._get_available_quantity(
                move.product_id, location, lot or False, strict=True
            )
            available = move.product_id.uom_id._compute_quantity(
                available_product_uom,
                move.product_uom,
                rounding_method="HALF-UP",
            )
            reserved_on_move = self._get_move_reserved_qty(
                move,
                location,
                lot or False,
            )
            available += reserved_on_move
            if float_compare(available, needed_qty, precision_rounding=precision) < 0:
                raise UserError(
                    _(
                        "Not enough %(product)s in %(location)s (needed %(needed).2f %(uom)s, available %(available).2f)."
                    )
                    % {
                        "product": move.product_id.display_name,
                        "location": location.display_name,
                        "needed": needed_qty,
                        "available": available,
                        "uom": move.product_uom.name,
                    }
                )

        return vals_list

    @staticmethod
    def _get_move_reserved_qty(move, location, lot=False):
        """Return quantity already reserved/entered on this move for the same lot/location."""
        rounding = move.product_uom.rounding or 0.000001
        qty = 0.0
        for line in move.move_line_ids:
            if (line.location_id or move.location_id) != location:
                continue
            if lot and line.lot_id != lot:
                continue
            if not lot and line.lot_id:
                continue
            line_qty = line.quantity or 0.0
            if line.product_uom_id and line.product_uom_id != move.product_uom:
                line_qty = line.product_uom_id._compute_quantity(
                    line_qty,
                    move.product_uom,
                    rounding_method="HALF-UP",
                )
            qty += line_qty
        return float_round(qty, precision_rounding=rounding)

    def _resolve_lot_for_move(self, move, picking, lot_id, lot_name, lot_model):
        if lot_id:
            return lot_id
        lot_name = (lot_name or "").strip()
        if lot_name:
            lot = lot_model.create(
                {
                    "name": lot_name,
                    "product_id": move.product_id.id,
                    "company_id": picking.company_id.id,
                }
            )
            return lot.id
        if move.product_id.tracking in ("lot", "serial"):
            raise UserError(
                _("Product %s requires a lot/serial number before validation.")
                % move.product_id.display_name
            )
        return False

    def _console_pending_pickings(self, production):
        """Return pending component pickings for a given MO.

        Primary source is ``production.picking_ids`` (standard Odoo
        relation). On some databases, backorder pickings keep the MO
        reference only in ``origin`` while still being linked in the
        smart button. To handle those safely (without assuming custom
        fields on ``stock.picking``), we:

        - filter ``production.picking_ids`` for component pickings
        - optionally add extra pickings with the same ``origin``,
          same picking type code and state, excluding ones we already
          have from the relation
        """
        picking_model = request.env[STOCK_PICKING_MODEL]
        preferred_codes = {"mrp_operation", "internal"}

        if not production or not production.exists():
            return picking_model.browse()

        # Base set: pickings directly linked to the MO
        base_pickings = production.picking_ids.filtered(
            lambda p: p.state not in ("cancel", "done")
            and p.picking_type_id.code in preferred_codes
        )

        # Extra set: pickings that share the same origin but are not
        # already linked through production.picking_ids (covers some
        # backorder scenarios).
        extra_domain = [
            ("state", "not in", ("cancel", "done")),
            ("picking_type_id.code", "in", list(preferred_codes)),
            ("origin", "=", production.name),
            ("id", "not in", base_pickings.ids or [0]),
        ]
        extra_pickings = picking_model.search(extra_domain)

        return base_pickings | extra_pickings

    def _console_sort_pickings(self, pickings):
        preferred_codes = {"mrp_operation", "internal"}

        def sort_key(picking):
            ready_priority = 0 if picking.state == "assigned" else 1
            code_priority = 0 if picking.picking_type_id.code in preferred_codes else 1
            sequence = picking.picking_type_id.sequence or 0
            return (ready_priority, code_priority, sequence, picking.id)

        # Return in ascending id order for predictable processing (older first).
        return pickings.sorted(key=sort_key)

    def _console_get_picking_production(self, picking):
        """Resolve MO from picking across Odoo variants safely."""
        if not picking or not picking.exists():
            return False
        # Standard field on manufacturing pickings
        if "production_id" in picking._fields:
            prod = picking.production_id
            if prod and prod.exists():
                return prod
        # Some dbs use a many2many production_ids
        if hasattr(picking, "production_ids"):
            prod = picking.production_ids[:1]
            if prod and prod.exists():
                return prod
        # Fallback: find by origin reference
        prod_model = request.env[MRP_PRODUCTION_MODEL]
        if picking.origin:
            prod = prod_model.search([("name", "=", picking.origin)], limit=1)
            if prod:
                return prod
        return False

    def _console_choose_picking(self, pickings):
        sorted_pickings = self._console_sort_pickings(pickings)
        return sorted_pickings[0] if sorted_pickings else False

    def _console_select_picking(self, production_id=None, picking_id=None):
        """Return a picking record to work on, or False."""
        picking_model = request.env[STOCK_PICKING_MODEL]
        production_model = request.env[MRP_PRODUCTION_MODEL]

        production = False
        selected_picking = False
        if picking_id:
            try:
                pid = int(picking_id)
            except (TypeError, ValueError):
                pid = False
            if pid:
                selected_picking = picking_model.browse(pid)
                if selected_picking.exists():
                    production = self._console_get_picking_production(selected_picking)
                else:
                    selected_picking = False
            else:
                selected_picking = False

        if not production and production_id:
            try:
                production = production_model.browse(int(production_id))
            except (TypeError, ValueError):
                production = False

        if not production or not production.exists():
            return False, False

        pending_pickings = self._console_pending_pickings(production)
        if not pending_pickings:
            return False, production

        if selected_picking and selected_picking in pending_pickings:
            picking = selected_picking
        else:
            picking = self._console_choose_picking(pending_pickings)

        return picking, production

    @http.route(
        "/mrp_parallel_console/get_picking_print_menu", type="json", auth="user"
    )
    def get_picking_print_menu(self):
        """Return list of available report actions for stock pickings."""
        _require_group("stock.group_stock_user")
        env = request.env
        reports = []
        for xmlid, label, description in PICKING_PRINT_REPORTS:
            action = env.ref(xmlid, raise_if_not_found=False)
            if not action:
                continue
            reports.append(
                {
                    "xml_id": xmlid,
                    "name": _(label),
                    "help": _(description),
                }
            )
        return {"reports": reports}

    @http.route(
        "/mrp_parallel_console/get_picking_print_action", type="json", auth="user"
    )
    def get_picking_print_action(self, picking_id=None, report_xml_id=None):
        """Return a specific print action for a stock picking."""
        _require_group("stock.group_stock_user")
        if not picking_id:
            return {"error": _("No picking ID provided.")}

        picking = request.env[STOCK_PICKING_MODEL].browse(picking_id)
        if not picking.exists():
            return {"error": _("Picking not found.")}

        if report_xml_id:
            report_action = request.env.ref(report_xml_id, raise_if_not_found=False)
            if not report_action:
                return {"error": _("The selected report is no longer available.")}
            try:
                action = report_action.report_action(picking)
            except Exception as exc:
                return {"error": str(exc)}
            return {"action": action}

        try:
            action = picking.do_print_picking()
        except Exception:
            fallback = request.env.ref(
                "stock.action_report_picking", raise_if_not_found=False
            )
            action = fallback.report_action(picking) if fallback else False

        if not action:
            return {"error": _("No print action available for this picking.")}
        return {"action": action}

    @http.route(
        "/mrp_parallel_console/get_production_print_menu", type="json", auth="user"
    )
    def get_production_print_menu(self):
        """Return all actions bound to the MO Print menu."""
        _require_group("mrp.group_mrp_user")
        model = request.env["ir.model"].search(
            [("model", "=", MRP_PRODUCTION_MODEL)], limit=1
        )
        if not model:
            return {"actions": []}

        actions = []
        report_model = request.env["ir.actions.report"]
        report_actions = report_model.search(
            [
                ("binding_model_id", "=", model.id),
                ("binding_type", "=", "report"),
            ]
        )
        for report in report_actions:
            actions.append(
                {
                    "id": report.id,
                    "name": report.name,
                    "model": "ir.actions.report",
                }
            )

        server_model = request.env["ir.actions.server"]
        server_actions = server_model.search(
            [
                ("binding_model_id", "=", model.id),
                ("binding_type", "=", "report"),
            ]
        )
        for srv in server_actions:
            actions.append(
                {
                    "id": srv.id,
                    "name": srv.name,
                    "model": "ir.actions.server",
                }
            )

        actions.sort(key=lambda item: item["name"].lower())
        return {"actions": actions}

    @http.route(
        "/mrp_parallel_console/get_production_print_action", type="json", auth="user"
    )
    def get_production_print_action(
        self, production_id=None, action_id=None, action_model=None
    ):
        """Execute a print action bound to manufacturing orders."""
        _require_group("mrp.group_mrp_user")
        if not production_id or not action_id or not action_model:
            return {"error": _("Missing parameters to print this manufacturing order.")}

        production = request.env[MRP_PRODUCTION_MODEL].browse(production_id)
        if not production.exists():
            return {"error": _("Manufacturing order not found.")}

        try:
            action_record = request.env[action_model].browse(int(action_id))
        except Exception:
            return {"error": _("Unable to locate the requested print action.")}
        if not action_record.exists():
            return {"error": _("Requested print action does not exist anymore.")}

        if action_model == "ir.actions.report":
            result_action = action_record.report_action(production)
            return {"action": result_action}

        if action_model == "ir.actions.server":
            ctx = dict(
                request.context,
                active_id=production.id,
                active_ids=[production.id],
                active_model=MRP_PRODUCTION_MODEL,
            )
            result = action_record.with_context(ctx).run()
            return {"action": result or False}

        return {"error": _("Unsupported action type: %s") % action_model}

    @http.route("/mrp_parallel_console/get_picking_action", type="json", auth="user")
    def get_picking_action(self, production_id=None, picking_id=None):
        """Open standard picking form (core views) in a modal."""
        _require_group("stock.group_stock_user")
        picking, production = self._console_select_picking(production_id, picking_id)
        if not picking:
            return {"error": "No pending component picking found for this MO."}

        # compute next picking in queue (for auto-chain)
        pending_pickings = self._console_pending_pickings(production)
        sorted_pickings = self._console_sort_pickings(pending_pickings)
        next_id = False
        if sorted_pickings and len(sorted_pickings) > 1:
            # current pick is first; next is second
            next_id = (
                sorted_pickings[1].id
                if sorted_pickings[0] == picking
                else sorted_pickings[0].id
            )

        # Try to reserve before opening
        if picking.state not in ("done", "cancel"):
            try:
                picking.action_assign()
            except Exception:
                pass

        # Auto-fill move lines so user can validate immediately (like one-click pick)
        self._auto_fill_move_lines(picking)

        if hasattr(picking, "action_view_picking"):
            action = picking.action_view_picking()
        else:
            action = {
                "type": "ir.actions.act_window",
                "res_model": "stock.picking",
                "view_mode": "form",
                "res_id": picking.id,
            }
        # Ensure views is defined to avoid client errors expecting map()
        action.setdefault("views", [(False, "form")])
        action["target"] = "new"
        return {"action": action, "next_picking_id": next_id}

    def _auto_fill_move_lines(self, picking):
        """Pre-create move lines using available quants so user only needs Validate."""


        Quant = request.env[STOCK_QUANT_MODEL]
        MoveLine = request.env["stock.move.line"]
        for move in picking.move_ids_without_package:
            rounding = move.product_uom.rounding or 0.000001
            existing_qty = 0.0
            for line in move.move_line_ids:
                existing_qty += (
                    getattr(line, "quantity", getattr(line, "qty_done", 0.0)) or 0.0
                )

            remaining = max((move.product_uom_qty or 0.0) - existing_qty, 0.0)
            remaining = float_round(remaining, precision_rounding=rounding)
            if remaining <= 0:
                continue

            # Non-tracked: one line for full remaining
            if move.product_id.tracking == "none":
                # If reserved lines already exist, update the first one instead of
                # creating a new line to avoid duplicates in the UI.
                if move.move_line_ids:
                    line = move.move_line_ids[0]
                    current_qty = (
                        getattr(line, "qty_done", getattr(line, "quantity", 0.0)) or 0.0
                    )
                    new_qty = current_qty + remaining
                    vals = {}
                    if "qty_done" in line._fields:
                        vals["qty_done"] = new_qty
                    if "quantity" in line._fields:
                        vals["quantity"] = new_qty
                    if vals:
                        line.write(vals)
                else:
                    MoveLine.create(
                        {
                            "move_id": move.id,
                            "picking_id": picking.id,
                            "company_id": picking.company_id.id,
                            "product_id": move.product_id.id,
                            "product_uom_id": move.product_uom.id,
                            "location_id": move.location_id.id
                            or picking.location_id.id,
                            "location_dest_id": picking.location_dest_id.id,
                            "qty_done": remaining,
                            "quantity": remaining,
                        }
                    )
                continue

            # Tracked: split by available quants FIFO — batch create to avoid large TX
            domain = [
                ("product_id", "=", move.product_id.id),
                (
                    "location_id",
                    "child_of",
                    move.location_id.id or picking.location_id.id,
                ),
                ("lot_id", "!=", False),
                ("quantity", ">", 0),
            ]
            quants = Quant.search(domain, order="in_date asc", limit=200)
            batch_vals = []
            for quant in quants:
                if remaining <= 0:
                    break
                available = Quant._get_available_quantity(
                    move.product_id,
                    quant.location_id,
                    lot_id=quant.lot_id,
                    package_id=quant.package_id,
                    owner_id=quant.owner_id,
                    strict=True,
                )
                if quant.product_uom_id != move.product_uom:
                    available = quant.product_uom_id._compute_quantity(
                        available,
                        move.product_uom,
                        rounding_method="HALF-UP",
                    )
                available = float_round(available, precision_rounding=rounding)
                if available <= 0:
                    continue
                take = min(available, remaining)
                take = float_round(take, precision_rounding=rounding)
                batch_vals.append(
                    {
                        "move_id": move.id,
                        "picking_id": picking.id,
                        "company_id": picking.company_id.id,
                        "product_id": move.product_id.id,
                        "product_uom_id": move.product_uom.id,
                        "location_id": quant.location_id.id,
                        "location_dest_id": picking.location_dest_id.id,
                        "lot_id": quant.lot_id.id,
                        "qty_done": take,
                        "quantity": take,
                    }
                )
                remaining -= take
            if batch_vals:
                MoveLine.with_context(no_recompute=True).create(batch_vals)


            # If still remaining (no quants), leave it empty for user to fill in form

    def _serialize_picking(self, picking):
        data = {
            "id": picking.id,
            "name": picking.name,
            "state": picking.state,
            "origin": picking.origin,
            "location_name": picking.location_id.display_name,
            "location_dest_name": picking.location_dest_id.display_name,
            "moves": [],
        }

        for move in picking.move_ids_without_package:
            data["moves"].append(self._serialize_move(move, picking))

        return data

    def _serialize_picking_option(self, picking):
        return {
            "id": picking.id,
            "name": picking.name,
            "operation": picking.picking_type_id.display_name,
            "code": picking.picking_type_id.code,
            "state": picking.state,
            "state_label": _selection_label(picking, "state", picking.state),
            "from": picking.location_id.display_name,
            "to": picking.location_dest_id.display_name,
        }

    def _serialize_move(self, move, picking):
        product = move.product_id
        on_hand = product.with_context(location=picking.location_id.id).qty_available
        move_location = move.location_id or picking.location_id
        lots = self._get_available_lots(product, move_location, move=move)
        locations = self._get_available_locations(product, move_location, move=move)
        return {
            "move_id": move.id,
            "product_id": product.id,
            "product_name": product.display_name,
            "product_tracking": product.tracking,
            "required_qty": move.product_uom_qty,
            "qty_done": getattr(move, "quantity_done", move.quantity),
            "uom": move.product_uom.name,
            "on_hand": on_hand,
            "location_id": move_location.id,
            "location_name": move_location.display_name,
            "move_lines": [
                {
                    "id": ml.id,
                    "lot_id": ml.lot_id.id if ml.lot_id else False,
                    "lot_name": ml.lot_id.display_name if ml.lot_id else "",
                    "qty_done": getattr(ml, "qty_done", None) or ml.quantity or 0.0,
                    "location_id": (ml.location_id or move_location).id,
                }
                for ml in move.move_line_ids
            ]
            or [
                {
                    "id": None,
                    "lot_id": False,
                    "lot_name": "",
                    "qty_done": move.quantity or move.product_uom_qty,
                    "location_id": move_location.id,
                }
            ],
            "available_lots": lots,
            "available_locations": locations,
        }

    def _get_available_lots(self, product, location, move=None):
        if product.tracking not in ("lot", "serial"):
            return []
        quant_model = request.env[STOCK_QUANT_MODEL]
        domain = [
            ("product_id", "=", product.id),
            ("location_id", "child_of", location.id),
            ("lot_id", "!=", False),
            ("quantity", ">", 0),
        ]
        groups = quant_model.read_group(
            domain,
            ["location_id", "lot_id", "quantity:sum", "reserved_quantity:sum"],
            ["location_id", "lot_id"],
            lazy=False,
        )
        lots = []
        for group in groups:
            if not group.get("lot_id") or not group.get("location_id"):
                continue
            lot = request.env[STOCK_LOT_MODEL].browse(group["lot_id"][0])
            loc = request.env["stock.location"].browse(group["location_id"][0])
            reserved_on_move = (
                self._get_move_reserved_qty(move, loc, lot)
                if move
                else 0.0
            )
            free_product_uom_qty = (
                (group.get("quantity") or 0.0)
                - (group.get("reserved_quantity") or 0.0)
            )
            if move and product.uom_id != move.product_uom:
                free_qty = product.uom_id._compute_quantity(
                    free_product_uom_qty,
                    move.product_uom,
                    rounding_method="HALF-UP",
                )
            else:
                free_qty = free_product_uom_qty
            quantity = free_qty + reserved_on_move
            if quantity <= 0:
                continue
            lots.append(
                {
                    "id": group["lot_id"][0],
                    "name": group["lot_id"][1],
                    "location_id": group["location_id"][0],
                    "location_name": group["location_id"][1],
                    "quantity": quantity,
                }
            )
        return lots

    def _get_available_locations(self, product, root_location=None, move=None):
        """Return locations under root that have stock for this product."""
        Quant = request.env["stock.quant"]
        Location = request.env["stock.location"]

        domain = [
            ("product_id", "=", product.id),
            ("location_id.usage", "in", ["internal", "transit"]),
            ("quantity", ">", 0),
        ]
        if root_location:
            domain.append(("location_id", "child_of", root_location.id))

        groups = Quant.read_group(
            domain,
            ["location_id", "quantity:sum", "reserved_quantity:sum"],
            ["location_id"],
            orderby="location_id",
        )

        locations = []
        for group in groups:
            if not group.get("location_id"):
                continue
            loc_id = group["location_id"][0]
            loc = Location.browse(loc_id)
            reserved_on_move = 0.0
            if move:
                for line in move.move_line_ids.filtered(
                    lambda ml, current_loc=loc: (ml.location_id or move.location_id) == current_loc
                ):
                    line_qty = line.quantity or 0.0
                    if line.product_uom_id and line.product_uom_id != move.product_uom:
                        line_qty = line.product_uom_id._compute_quantity(
                            line_qty,
                            move.product_uom,
                            rounding_method="HALF-UP",
                        )
                    reserved_on_move += line_qty
            free_product_uom_qty = (
                (group.get("quantity") or 0.0)
                - (group.get("reserved_quantity") or 0.0)
            )
            if move and product.uom_id != move.product_uom:
                free_qty = product.uom_id._compute_quantity(
                    free_product_uom_qty,
                    move.product_uom,
                    rounding_method="HALF-UP",
                )
            else:
                free_qty = free_product_uom_qty
            free_qty += reserved_on_move
            if free_qty <= 0:
                continue
            locations.append(
                {
                    "id": loc.id,
                    "name": loc.complete_name or loc.display_name,
                    "on_hand": free_qty,
                }
            )
        return locations
