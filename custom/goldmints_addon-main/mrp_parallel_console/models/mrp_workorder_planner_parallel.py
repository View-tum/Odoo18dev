# -*- coding: utf-8 -*-
# Keep core workorder planning untouched so Odoo schedules resources normally.

from odoo import models


class MrpWorkorder(models.Model):
    _inherit = "mrp.workorder"

    def _plan_workorder(self, replan=False):
        """Delegate entirely to the standard planner."""
        return super()._plan_workorder(replan=replan)

