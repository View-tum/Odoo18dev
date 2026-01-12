# -*- coding: utf-8 -*-
from odoo import api, fields, models


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    mps_batch_id = fields.Many2one(
        "mrp.mps.batch",
        string="MPS Group",
        related="procurement_group_id.mps_batch_id",
        store=True,
        readonly=True,
        index=True,
    )

    is_from_mps = fields.Boolean(string="From MPS", compute="_compute_is_from_mps", store=True, index=True)

    @api.depends("mps_batch_id")
    def _compute_is_from_mps(self):
        for mo in self:
            mo.is_from_mps = bool(mo.mps_batch_id)
