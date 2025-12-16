# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    mpc_qc_block_close = fields.Boolean(
        string="Block MO Close if QC Pending",
        default=True,
        help="If enabled, Closing/Validating a Manufacturing Order from the parallel console will be blocked until all related quality checks are passed or failed. Workorders can still be marked Done without QC.",
    )
