import os
import re

file_path = r'c:\365_project\TheCool18e\Dev\custom\goldmints_addon-main\mrp_parallel_console\controllers\mrp_parallel_console.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find the start of the method
start_pattern = r'    @http\.route\("/mrp_parallel_console/get_data", type="json", auth="user"\)\n    def get_data\(self, production_id=None\):'
match = re.search(start_pattern, content)
if not match:
    print("Could not find start pattern")
    exit(1)

start_idx = match.start()

# Find the end of the method (next method or comment block)
end_pattern = r'\n    # ---------------------------------------------------------\n    # Update console fields \(qty, dates, employees\)'
match_end = re.search(end_pattern, content[start_idx:])
if not match_end:
    print("Could not find end pattern")
    exit(1)

end_idx = start_idx + match_end.start()

old_method = content[start_idx:end_idx]

new_method = '''    @http.route("/mrp_parallel_console/get_data", type="json", auth="user")
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
        }'''

new_content = content[:start_idx] + new_method + content[end_idx:]

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Successfully replaced get_data method!")
