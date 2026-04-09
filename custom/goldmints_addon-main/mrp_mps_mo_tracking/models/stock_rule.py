# -*- coding: utf-8 -*-
import logging

from odoo import models

_logger = logging.getLogger(__name__)


class StockRule(models.Model):
    _inherit = "stock.rule"

    def _is_group_mto(self, group):
        if not group:
            return False
        mo = self.env["mrp.production"].sudo().search([
            ("procurement_group_id", "=", group.id),
            ("source_sale_order_id", "!=", False),
        ], limit=1)
        return bool(mo)

    def _prepare_mo_vals(
        self, product_id, product_qty, product_uom, location_dest_id,
        name, origin, company_id, values, bom
    ):
        res = super()._prepare_mo_vals(
            product_id, product_qty, product_uom, location_dest_id,
            name, origin, company_id, values, bom
        )

        group = values.get("group_id")
        if isinstance(group, int):
            group = self.env["procurement.group"].browse(group)
        if group:
            group = group.exists()

        ctx_batch_id = self.env.context.get("mps_active_batch_id")
        if ctx_batch_id and group and not group.mps_batch_id and not self._is_group_mto(group):
            group.write({"mps_batch_id": ctx_batch_id})

        return res
