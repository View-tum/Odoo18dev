# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare

MRP_WORKORDER_MODEL = "mrp.workorder"
UOM_DIGITS = "Product Unit of Measure"
QTY_WIZARD_MODEL = "mrp.parallel.console.qty.wizard"
QTY_WIZARD_LINE_MODEL = "mrp.parallel.console.qty.wizard.line"
WINDOW_CLOSE_ACTION = {"type": "ir.actions.act_window_close"}


class MrpParallelConsoleQtyWizard(models.TransientModel):
    _name = QTY_WIZARD_MODEL
    _description = "Parallel Console Quantity Wizard"

    # -------------------------------------------------------------------------
    # Defaults
    # -------------------------------------------------------------------------
    def _default_workorders(self):
        ids = (
            self.env.context.get("default_workorder_ids")
            or self.env.context.get("active_ids")
            or []
        )
        return self.env[MRP_WORKORDER_MODEL].browse(ids)

    workorder_ids = fields.Many2many(
        MRP_WORKORDER_MODEL,
        string="Work Orders",
        default=_default_workorders,
        readonly=True,
    )

    production_id = fields.Many2one(
        "mrp.production",
        string="Manufacturing Order",
        compute="_compute_production_id",
        store=False,
        readonly=True,
    )

    def _default_line_ids(self):
        lines = []
        for workorder in self._default_workorders():
            lines.append(
                (
                    0,
                    0,
                    {
                        "workorder_id": workorder.id,
                        "recorded_qty": workorder.console_qty or 0.0,
                        "lot_id": workorder.finished_lot_id.id,
                    },
                )
            )
        return lines

    line_ids = fields.One2many(
        QTY_WIZARD_LINE_MODEL,
        "wizard_id",
        string="Workorder Lines",
        default=_default_line_ids,
    )

    def _compute_production_id(self):
        for wizard in self:
            productions = wizard.workorder_ids.mapped("production_id")
            if len(set(productions.ids)) == 1:
                wizard.production_id = productions[:1]
            else:
                wizard.production_id = False

    def action_open_create_lot_wizard(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError("Please select at least one workorder line before creating a lot.")
        if not self.production_id:
            raise UserError(
                "All selected workorders must belong to the same manufacturing order to create a lot."
            )
        product = self.production_id.product_id
        if not product:
            raise UserError("The manufacturing order doesn't define a finished product.")

        return {
            "type": "ir.actions.act_window",
            "name": "Create LOT",
            "res_model": "mrp.parallel.console.create.lot.wizard",
            "view_mode": "form",
            "view_id": self.env.ref(
                "mrp_parallel_console.view_parallel_console_create_lot_wizard_form"
            ).id,
            "target": "new",
            "context": {
                "default_qty_wizard_id": self.id,
                "default_line_ids": [(6, 0, self.line_ids.ids)],
                "default_product_id": product.id,
                "default_company_id": self.production_id.company_id.id,
            },
        }

    # ---------------------------------------------------------------------
    # Apply
    # ---------------------------------------------------------------------
    def action_apply(self):
        self.ensure_one()
        if not self.line_ids:
            return WINDOW_CLOSE_ACTION.copy()
        productions = self.env["mrp.production"]
        affected_workorders = self.env[MRP_WORKORDER_MODEL]
        updated_payload = []
        for line in self.line_ids:
            if line.recorded_qty <= 0:
                raise UserError(
                    "Please enter a positive quantity for work order %s." % line.display_name
                )
            workorder = line.workorder_id
            rounding = workorder.production_id.product_uom_id.rounding or 0.0001
            if workorder.product_tracking in ("lot", "serial") and not line.lot_id:
                raise UserError(
                    "Please select a finished lot/serial number for work order %s before applying quantities."
                    % line.display_name
                )
            if (
                float_compare(
                    line.recorded_qty,
                    workorder.qty_produced,
                    precision_rounding=rounding,
                )
                < 0
            ):
                raise UserError(
                    "Work order %s already produced %.2f, you cannot set console quantities to %.2f."
                    % (workorder.display_name, workorder.qty_produced, line.recorded_qty)
                )
            vals = {
                "console_qty": line.recorded_qty,
                "qty_produced": line.recorded_qty,
            }
            if line.lot_id:
                vals["finished_lot_id"] = line.lot_id.id
            workorder.write(vals)
            productions |= workorder.production_id
            affected_workorders |= workorder
            updated_payload.append(
                {
                    "id": workorder.id,
                    "console_qty": line.recorded_qty,
                    "qty_produced": line.recorded_qty,
                    "finished_lot_name": line.lot_id.display_name if line.lot_id else "",
                    "finished_lot_id": line.lot_id.id if line.lot_id else False,
                }
            )

        for production in productions:
            if not production:
                continue
            total_console_qty = sum(production.workorder_ids.mapped("console_qty"))
            production.qty_producing = total_console_qty

            if production.product_tracking not in ("lot", "serial"):
                continue
            # Auto-fill MO lot_producing_id when there is a unique finished lot
            # across all workorders of the production. This keeps the MO Lot/Serial
            # field in sync with Set Qty / workorder lots.
            lots = {
                wo.finished_lot_id.id
                for wo in production.workorder_ids
                if wo.finished_lot_id
            }
            if len(lots) == 1:
                production.lot_producing_id = next(iter(lots))

        parallel_wos = affected_workorders.filtered(
            lambda w: w.operation_id.parallel_mode == "parallel"
            and w.state not in ("done", "cancel")
        )
        if parallel_wos:
            parallel_wos._recompute_parallel_siblings()

        result = WINDOW_CLOSE_ACTION.copy()
        context = dict(result.get("context") or {})
        context.update(
            {
                "mrp_parallel_console_updates": updated_payload,
                "mrp_parallel_console_production_ids": productions.ids,
            }
        )
        result["context"] = context
        return result


class MrpParallelConsoleQtyWizardLine(models.TransientModel):
    _name = QTY_WIZARD_LINE_MODEL
    _description = "Parallel Console Quantity Wizard Line"

    wizard_id = fields.Many2one(
        "mrp.parallel.console.qty.wizard",
        required=True,
        ondelete="cascade",
    )
    workorder_id = fields.Many2one(
        MRP_WORKORDER_MODEL,
        readonly=True,
    )
    workorder_name = fields.Char(related="workorder_id.display_name", store=False)
    operation_name = fields.Char(compute="_compute_operation_name", store=False)
    workcenter_id = fields.Many2one(
        "mrp.workcenter",
        related="workorder_id.workcenter_id",
        store=False,
        readonly=True,
    )
    product_id = fields.Many2one(
        "product.product",
        related="workorder_id.product_id",
        store=False,
        readonly=True,
    )
    company_id = fields.Many2one(
        "res.company",
        related="workorder_id.company_id",
        store=False,
        readonly=True,
    )
    planned_qty = fields.Float(
        related="workorder_id.planned_qty",
        digits=UOM_DIGITS,
        store=False,
        readonly=True,
    )
    produced_qty = fields.Float(
        related="workorder_id.qty_produced",
        digits=UOM_DIGITS,
        store=False,
        readonly=True,
    )
    recorded_qty = fields.Float(
        string="Quantity",
        digits=UOM_DIGITS,
    )
    lot_id = fields.Many2one(
        "stock.lot",
        string="Finished Lot/Serial",
        domain="[('product_id', '=', product_id), ('company_id', '=', company_id)]",
        check_company=True,
    )

    display_name = fields.Char(compute="_compute_display_name")

    @api.depends("workorder_name", "workcenter_id")
    def _compute_display_name(self):
        for line in self:
            workcenter = line.workcenter_id.display_name or ""
            line.display_name = "%s (%s)" % (line.workorder_name or "", workcenter)

    @api.onchange("lot_id")
    def _onchange_lot_id_propagate(self):
        """When a lot is chosen/created on one line, reuse it on
        other lines of the same wizard for the same product that do
        not have a lot yet.
        """
        for line in self:
            if not line.lot_id or not line.wizard_id:
                continue
            siblings = line.wizard_id.line_ids.filtered(
                lambda l, current_line=line: l.id != current_line.id
                and not l.lot_id
                and l.product_id == current_line.product_id
            )
            siblings.lot_id = line.lot_id

    @api.depends("workorder_id.operation_id", "workorder_name")
    def _compute_operation_name(self):
        for line in self:
            operation_name = line.workorder_id.operation_id.display_name
            if not operation_name:
                name_parts = (line.workorder_name or "").split(" - ", 1)
                operation_name = name_parts[1] if len(name_parts) == 2 else line.workorder_name
            line.operation_name = operation_name

class MrpParallelConsoleCreateLotWizard(models.TransientModel):
    _name = "mrp.parallel.console.create.lot.wizard"
    _description = "Parallel Console Create Lot Wizard"

    qty_wizard_id = fields.Many2one(
        QTY_WIZARD_MODEL,
        required=True,
        ondelete="cascade",
    )
    line_ids = fields.Many2many(
        QTY_WIZARD_LINE_MODEL,
        "mrp_parallel_console_create_lot_rel",
        "create_lot_id",
        "qty_line_id",
        string="Workorder Lines",
        required=True,
    )
    product_id = fields.Many2one("product.product", required=True, readonly=True)
    company_id = fields.Many2one("res.company", required=True, readonly=True)
    lot_name = fields.Char(string="Lot Name", required=True)

    def action_create_and_apply(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError("Select at least one workorder line to apply the newly created lot.")
        lot = self.env["stock.lot"].create(
            {
                "name": self.lot_name,
                "product_id": self.product_id.id,
                "company_id": self.company_id.id,
            }
        )
        self.line_ids.write({"lot_id": lot.id})
        return WINDOW_CLOSE_ACTION.copy()


class MrpParallelAssignLotWizard(models.TransientModel):
    _name = "mrp.parallel.assign.lot.wizard"
    _description = "Assign LOT to Production"

    production_id = fields.Many2one(
        "mrp.production",
        string="Manufacturing Order",
        required=True,
    )
    product_id = fields.Many2one(
        related="production_id.product_id",
        string="Product",
        readonly=True,
    )
    lot_id = fields.Many2one(
        "stock.lot",
        string="LOT / Serial",
        domain="[('product_id', '=', product_id)]",
    )

    def action_create_lot(self):
        self.ensure_one()
        product = self.product_id
        company = self.production_id.company_id
        sequence = getattr(product, "lot_sequence_id", False)
        lot_name = False
        if sequence:
            lot_name = sequence.next_by_id()
        if not lot_name:
            lot_name = (
                self.env["ir.sequence"].next_by_code("stock.lot.serial")
                or f"{product.display_name}-{fields.Date.today()}"
            )
        lot = self.env["stock.lot"].create(
            {
                "name": lot_name,
                "product_id": product.id,
                "company_id": company.id,
            }
        )
        self.lot_id = lot.id
        # stay on the wizard and let the form reflect the new value
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
            "context": dict(self.env.context),
        }

    def action_confirm(self):
        self.ensure_one()
        mo = self.production_id
        if not self.lot_id:
            raise UserError("Please select or create a LOT/Serial number before confirming.")

        # Write LOT on MO and workorders, using both standard fields
        # and optional custom final_lot_id when present.
        if hasattr(mo, "final_lot_id"):
            mo.final_lot_id = self.lot_id.id
        mo.lot_producing_id = self.lot_id.id

        for wo in mo.workorder_ids:
            if hasattr(wo, "final_lot_id"):
                wo.final_lot_id = self.lot_id.id
            if "finished_lot_id" in wo._fields:
                wo.finished_lot_id = self.lot_id.id

        return {
            "type": "ir.actions.client",
            "tag": "mrp_parallel_console.main_console",
            "name": "Workorder Parallel Console",
            "context": {
                "default_production_id": mo.id,
                "active_id": mo.id,
                "active_model": "mrp.production",
            },
            "params": {
                "production_id": mo.id,
            },
        }
