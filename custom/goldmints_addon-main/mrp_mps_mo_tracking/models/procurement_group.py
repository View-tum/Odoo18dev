# -*- coding: utf-8 -*-
from odoo import fields, models


class ProcurementGroup(models.Model):
    _inherit = "procurement.group"

    mps_batch_id = fields.Many2one("mrp.mps.batch", string="MPS Batch", index=True)

    def _get_mto_group_ids(self):
        """Return procurement.group IDs that are already tied to MTO (Sales) MOs."""
        if not self:
            return set()
        mo_model = self.env["mrp.production"].sudo()
        mto_mos = mo_model.search([
            ("procurement_group_id", "in", self.ids),
            ("source_sale_order_id", "!=", False),
        ])
        return set(mto_mos.mapped("procurement_group_id").ids)

    def run(self, procurements, raise_user_error=True):
        ctx_batch_id = self.env.context.get("mps_active_batch_id")

        if ctx_batch_id:
            for procurement in procurements:
                if isinstance(procurement.values, dict):
                    procurement.values["mps_active_batch_id"] = ctx_batch_id

        res = super().run(procurements, raise_user_error=raise_user_error)

        if ctx_batch_id:
            groups = self.env["procurement.group"]
            for procurement in procurements:
                group = procurement.values.get("group_id")
                if group:
                    if isinstance(group, int):
                        group = self.env["procurement.group"].browse(group)
                    if group:
                        groups |= group

            mto_group_ids = self._get_mto_group_ids() if groups else set()
            groups_to_update = groups.filtered(
                lambda g: (not g.mps_batch_id) and (g.id not in mto_group_ids)
            )
            if groups_to_update:
                groups_to_update.write({"mps_batch_id": ctx_batch_id})

        return res
