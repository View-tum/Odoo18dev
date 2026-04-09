# -*- coding: utf-8 -*-
from odoo import fields, models


class MrpMpsBatch(models.Model):
    _name = "mrp.mps.batch"
    _description = "MPS Batch (Order Run)"
    _order = "id desc"

    name = fields.Char(
        required=True,
        readonly=True,
        default=lambda self: self.env["ir.sequence"].next_by_code("mrp.mps.batch") or "MPS0000",
    )
    user_id = fields.Many2one("res.users", readonly=True, default=lambda self: self.env.user)
    note = fields.Char()
