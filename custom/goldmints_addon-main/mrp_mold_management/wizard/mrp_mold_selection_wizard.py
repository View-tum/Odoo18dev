# -*- coding: utf-8 -*-
from odoo import api, fields, models


class MrpMoldSelectionWizard(models.TransientModel):
    _name = "mrp.mold.selection.wizard"
    _description = "Machine & Mold Selection Wizard"

    workorder_id = fields.Many2one("mrp.workorder", string="Work Order", readonly=True)
    production_id = fields.Many2one("mrp.production", string="Manufacturing Order", readonly=True)
    product_id = fields.Many2one("product.product", string="Product", readonly=True)

    line_ids = fields.One2many(
        "mrp.mold.selection.wizard.line",
        "wizard_id",
        string="Compatible Combinations"
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_id = self.env.context.get("active_id")
        active_model = self.env.context.get("active_model")

        if not active_id or not active_model:
            return res

        product = False
        lines = []

        if active_model == "mrp.production":
            mo = self.env["mrp.production"].browse(active_id)
            res.update({"production_id": mo.id, "product_id": mo.product_id.id})
            product = mo.product_id
        elif active_model == "mrp.workorder":
            wo = self.env["mrp.workorder"].browse(active_id)
            res.update({"workorder_id": wo.id, "product_id": wo.product_id.id})
            product = wo.product_id

        if product:
            matrix_lines = self.env["mrp.mold.matrix.report"].search(
                [("product_id", "=", product.id)]
            ).sorted(
                key=lambda ml: (
                    0
                    if ml.mold_state == "normal"
                    else 1 if ml.mold_state == "warning" else 2,
                    ml.machine_id.display_name or "",
                    ml.mold_id.display_name or "",
                )
            )
            for ml in matrix_lines:
                lines.append(
                    (
                        0,
                        0,
                        {
                            "matrix_line_id": ml.id,
                            "machine_id": ml.machine_id.id,
                            "mold_id": ml.mold_id.id,
                            "cycle_time": ml.cycle_time,
                            "units_per_hour": ml.units_per_hour,
                            "mold_state": ml.mold_state,
                            "shots_remaining": ml.mold_id.mold_life_limit
                            - ml.mold_id.mold_life_current
                            if ml.mold_id.mold_life_limit
                            else 0,
                        },
                    )
                )

        res["line_ids"] = lines
        return res

class MrpMoldSelectionWizardLine(models.TransientModel):
    _name = "mrp.mold.selection.wizard.line"
    _description = "Selection Wizard Line"

    wizard_id = fields.Many2one("mrp.mold.selection.wizard", string="Wizard")
    matrix_line_id = fields.Integer(string="Matrix Line ID") # Pointer to the SQL view row
    machine_id = fields.Many2one("mrp.workcenter", string="Machine")
    mold_id = fields.Many2one("mrp.workcenter", string="Mold")
    cycle_time = fields.Float(string="Cycle Time (s)")
    units_per_hour = fields.Float(string="Units / Hour")
    mold_state = fields.Selection(
        [("normal", "Normal"), ("warning", "Warning"), ("full", "Full")],
        string="Status"
    )
    shots_remaining = fields.Integer(string="Remaining Shots")

    def action_select(self):
        self.ensure_one()
        wizard = self.wizard_id
        if wizard.production_id:
            # Apply to MO (first workorder as a sample or all?)
            # Usually users want to switch the machine for the MO's main operation
            for wo in wizard.production_id.workorder_ids:
                wo.workcenter_id = self.machine_id
                if "mold_ids" in wo._fields:
                    wo.mold_ids = [(6, 0, [self.mold_id.id])]
        elif wizard.workorder_id:
            wizard.workorder_id.workcenter_id = self.machine_id
            if "mold_ids" in wizard.workorder_id._fields:
                wizard.workorder_id.mold_ids = [(6, 0, [self.mold_id.id])]

        return {"type": "ir.actions.act_window_close"}


class MrpMoldWarningWizard(models.TransientModel):
    _name = "mrp.mold.warning.wizard"
    _description = "Mold Life Warning Wizard"

    production_id = fields.Many2one("mrp.production", string="Manufacturing Order", readonly=True)
    message = fields.Text(string="Warning Message", readonly=True)

    def action_confirm_anyway(self):
        self.ensure_one()
        # Call action_confirm with context to skip the check
        return self.production_id.with_context(skip_mold_check=True).action_confirm()

    def action_select_alternative(self):
        self.ensure_one()
        # Open the selection wizard instead
        action = self.env["ir.actions.actions"]._for_xml_id("mrp_mold_management.action_mrp_mold_selection_wizard")
        action['context'] = {
            'active_id': self.production_id.id,
            'active_model': 'mrp.production',
        }
        return action
