from odoo import _, api, fields, models
from odoo.exceptions import UserError


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    def _mold_bom_reference_key(self, bom_or_ref):
        if hasattr(bom_or_ref, "code"):
            ref = (
                bom_or_ref.code
                or getattr(bom_or_ref, "name", False)
                or bom_or_ref.display_name
            )
        else:
            ref = bom_or_ref
        ref = (ref or "").strip()
        if not ref:
            return ""
        if ":" in ref:
            ref = ref.split(":", 1)[0].strip()
        if "-" in ref:
            return ref.rsplit("-", 1)[0]
        return ref

    def _get_mold_boms(self):
        self.ensure_one()
        if not self.product_tmpl_id:
            return self.env["mrp.bom"]
        domain = [
            ("type", "=", "normal"),
            ("product_tmpl_id", "=", self.product_tmpl_id.id),
            ("company_id", "in", [self.company_id.id, False]),
            "|",
            ("product_id", "=", self.product_id.id),
            ("product_id", "=", False),
        ]
        boms = self.env["mrp.bom"].search(domain)
        return boms.filtered(
            lambda b: b.operation_ids.filtered(
                lambda op: op.mold_ids
            )
        )

    def _has_started_workorders(self):
        self.ensure_one()
        wos = self.workorder_ids
        if wos.filtered(lambda wo: wo.state in ("progress", "done")):
            return True
        if wos.filtered(lambda wo: wo.qty_produced):
            return True
        return False

    def _get_mold_boms_same_reference(self):
        self.ensure_one()
        if not self.bom_id:
            return self._get_mold_boms()
        boms = self.env["mrp.bom"].search(
            [
                ("type", "=", "normal"),
                ("company_id", "in", [self.company_id.id, False]),
            ]
        )
        base_ref = self._mold_bom_reference_key(self.bom_id)
        if not base_ref:
            return self._get_mold_boms()
        boms = boms.filtered(
            lambda b: self._mold_bom_reference_key(b) == base_ref
        )
        return boms.filtered(
            lambda b: b.operation_ids.filtered(
                lambda op: op.mold_ids
            )
        )

    def action_change_mold_bom(self):
        self.ensure_one()
        if self.state != "confirmed":
            raise UserError(_("BOM can be changed only on Confirmed Manufacturing Orders."))
        if self._has_started_workorders():
            raise UserError(
                _(
                    "This MO already started. Please close the current MO (create backorder) "
                    "before changing the BOM."
                )
            )
        return {
            "type": "ir.actions.act_window",
            "res_model": "mrp.production.mold.bom.change.wizard",
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "new",
            "context": {"default_production_id": self.id},
        }

    def action_confirm(self):
        if self.env.context.get("show_mold_bom_wizard") and not self.env.context.get(
            "skip_mold_bom_wizard"
        ):
            if len(self) > 1:
                need = self.filtered(
                    lambda mo: mo.state == "draft" and len(mo._get_mold_boms()) > 1
                )
                if need:
                    raise UserError(
                        _("Please confirm one Manufacturing Order at a time to select a Mold BoM.")
                    )
                return super().action_confirm()

            mo = self
            if mo.state == "draft":
                mold_boms = mo._get_mold_boms()
                if mold_boms:
                    if len(mold_boms) == 1 and mo.bom_id != mold_boms[:1]:
                        mo._link_bom(mold_boms[:1])
                    elif len(mold_boms) > 1:
                        return {
                            "type": "ir.actions.act_window",
                            "res_model": "mrp.production.mold.bom.wizard",
                            "view_mode": "form",
                            "views": [(False, "form")],
                            "target": "new",
                            "context": {"default_production_id": mo.id},
                        }
        return super().action_confirm()


class MrpProductionMoldBomWizard(models.TransientModel):
    _name = "mrp.production.mold.bom.wizard"
    _description = "Select Mold BoM"

    production_id = fields.Many2one(
        "mrp.production", string="Manufacturing Order", required=True, readonly=True
    )
    available_bom_ids = fields.Many2many(
        "mrp.bom", compute="_compute_available_bom_ids", readonly=True
    )
    bom_id = fields.Many2one(
        "mrp.bom",
        string="Bill of Material",
        required=True,
        domain="[('id', 'in', available_bom_ids)]",
    )

    @api.depends("production_id")
    def _compute_available_bom_ids(self):
        for wizard in self:
            if wizard.production_id:
                wizard.available_bom_ids = wizard.production_id._get_mold_boms()
            else:
                wizard.available_bom_ids = False

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        production_id = res.get("production_id")
        if production_id:
            mo = self.env["mrp.production"].browse(production_id)
            mold_boms = mo._get_mold_boms()
            if mo.bom_id in mold_boms:
                res["bom_id"] = mo.bom_id.id
            elif mold_boms:
                res["bom_id"] = mold_boms[0].id
        return res

    def action_apply(self):
        self.ensure_one()
        mo = self.production_id
        if not mo or mo.state != "draft":
            return {"type": "ir.actions.act_window_close"}
        if self.bom_id:
            mo._link_bom(self.bom_id)
        return mo.with_context(skip_mold_bom_wizard=True).action_confirm()


class MrpProductionMoldBomChangeWizard(models.TransientModel):
    _name = "mrp.production.mold.bom.change.wizard"
    _description = "Change Mold BoM (Confirmed MO)"

    production_id = fields.Many2one(
        "mrp.production", string="Manufacturing Order", required=True, readonly=True
    )
    available_bom_ids = fields.Many2many(
        "mrp.bom", compute="_compute_available_bom_ids", readonly=True
    )
    bom_id = fields.Many2one(
        "mrp.bom",
        string="Bill of Material",
        required=True,
        domain="[('id', 'in', available_bom_ids)]",
    )

    @api.depends("production_id")
    def _compute_available_bom_ids(self):
        for wizard in self:
            if wizard.production_id:
                wizard.available_bom_ids = (
                    wizard.production_id._get_mold_boms_same_reference()
                )
            else:
                wizard.available_bom_ids = False

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        production_id = res.get("production_id")
        if production_id:
            mo = self.env["mrp.production"].browse(production_id)
            mold_boms = mo._get_mold_boms_same_reference()
            if mo.bom_id in mold_boms:
                res["bom_id"] = mo.bom_id.id
            elif mold_boms:
                res["bom_id"] = mold_boms[0].id
        return res

    def action_apply(self):
        self.ensure_one()
        mo = self.production_id
        if not mo or mo.state != "confirmed":
            return {"type": "ir.actions.act_window_close"}
        if mo._has_started_workorders():
            raise UserError(
                _(
                    "This MO already started. Please close the current MO (create backorder) "
                    "before changing the BOM."
                )
            )
        if self.bom_id:
            # Rebuild workorders cleanly to avoid core guard when relinking.
            if mo.workorder_ids:
                mo.workorder_ids.unlink()
            try:
                mo._link_bom(self.bom_id)
            except UserError as e:
                msg = str(e)
                if "You cannot link this work order to another manufacturing order" in msg:
                    raise UserError(
                        _(
                            "This MO already started or has workorders linked. "
                            "Please close the current MO (create backorder) before changing the BOM."
                        )
                    )
                raise
        return {"type": "ir.actions.act_window_close"}
