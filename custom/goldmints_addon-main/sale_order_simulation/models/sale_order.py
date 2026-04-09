from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    is_simulation_mode = fields.Boolean(
        string="Simulation Mode", default=False, index=True, copy=False
    )
    simulation_origin_id = fields.Many2one(
        "sale.order", string="Simulation Origin", index=True, copy=False
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("is_simulation_mode"):
                vals["state"] = "draft"
        return super().create(vals_list)

    def write(self, vals):
        # Nuclear guard to block any state change if it's not going back to draft/cancel
        if "state" in vals:
            for record in self:
                if record.is_simulation_mode and vals["state"] not in ("draft", "cancel"):
                    raise UserError(_("State changes are restricted in Simulation Mode. (Attempted: %s)") % vals["state"])
        return super().write(vals)

    @api.depends("is_simulation_mode")
    def _calc_approval_user_ids(self):
        # This is for compatibility with oi_workflow
        if hasattr(super(), "_calc_approval_user_ids"):
            super()._calc_approval_user_ids()
        for record in self:
            if record.is_simulation_mode:
                record.user_can_approve = False
                if hasattr(record, "approval_user_ids"):
                    record.approval_user_ids = False

    def approval_action_button(self, button_id):
        # Guard for oi_workflow buttons
        self.ensure_one()
        if self.is_simulation_mode:
            button = self.env["approval.buttons"].browse(button_id)
            if button.action_type in ("approve", "reject", "cancel_workflow"):
                raise UserError(_("Approval actions are disabled in Simulation Mode."))
        return super().approval_action_button(button_id)

    def action_confirm(self):
        if any(self.mapped("is_simulation_mode")):
            raise UserError(_("Confirmation is disabled in Simulation Mode."))
        return super().action_confirm()

    def action_sale_ok(self):
        if any(self.mapped("is_simulation_mode")):
            raise UserError(_("Confirmation is disabled in Simulation Mode."))
        # This is for dev_customer_credit_limit compatibility
        return super().action_sale_ok() if hasattr(super(), "action_sale_ok") else False

    def action_open_simulation(self):
        self.ensure_one()

        default_vals = self.copy_data()[0]

        # Use exact name as requested by user
        simulation_name = self.name

        default_vals.update(
            {
                "is_simulation_mode": True,
                "simulation_origin_id": self.id,
                "name": simulation_name,
                "state": "draft",
                "commitment_date": self.commitment_date,
                "proforma_invoice_no": self.proforma_invoice_no,
            }
        )

        simulation_so = self.create(default_vals)

        return {
            "name": _("Simulation Mode (Edit & Print)"),
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "res_id": simulation_so.id,
            "view_mode": "form",
            "target": "current",
            "context": {"create": False, "delete": True},
        }

    def action_simulation_cleanup(self):
        self.ensure_one()
        if self.is_simulation_mode:
            origin_id = self.simulation_origin_id.id
            self.unlink()
            if origin_id:
                return {
                    "type": "ir.actions.act_window",
                    "res_model": "sale.order",
                    "res_id": origin_id,
                    "view_mode": "form",
                    "target": "current",
                }
        return {"type": "ir.actions.act_window_close"}

    @api.model
    def _cron_cleanup_simulation_orders(self):
        expiry_date = fields.Datetime.now() - timedelta(days=1)
        simulations = self.search(
            [("is_simulation_mode", "=", True), ("create_date", "<", expiry_date)]
        )
        if simulations:
            simulations.unlink()

    @api.model
    def _get_view(self, view_id=None, view_type="form", **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == "form":

            for node in arch.xpath("//header//button | //button[contains(@name, 'approval')] | //button[contains(@name, 'confirm')]"):
                btn_name = node.get("name")
                if btn_name == "action_simulation_cleanup":
                    continue
                invisible = node.get("invisible")
                if not invisible:
                    node.set("invisible", "is_simulation_mode")
                elif "is_simulation_mode" not in str(invisible):
                    node.set("invisible", f"({invisible}) or is_simulation_mode")
        return arch, view
