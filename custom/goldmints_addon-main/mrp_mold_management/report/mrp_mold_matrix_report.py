# -*- coding: utf-8 -*-
from odoo import fields, models, tools


class MrpMoldMatrixReport(models.Model):
    _name = "mrp.mold.matrix.report"
    _description = "Mold Compatibility Matrix Report"
    _auto = False
    _rec_name = "machine_id"

    machine_id = fields.Many2one("mrp.workcenter", string="Machine", readonly=True)
    mold_id = fields.Many2one("mrp.workcenter", string="Mold", readonly=True)
    product_id = fields.Many2one("product.product", string="Product", readonly=True)
    mold_life_current = fields.Integer(string="Current Shots", readonly=True)
    mold_life_limit = fields.Integer(string="Shot Limit", readonly=True)
    mold_state = fields.Selection(
        [("normal", "Normal"), ("warning", "Warning"), ("full", "Full")],
        string="Mold Status",
        readonly=True,
    )
    cycle_time = fields.Float(string="Cycle Time (s)", readonly=True)
    units_per_hour = fields.Float(string="Units / Hour", readonly=True)

    def init(self):
        # Check if dependencies exist before creating view
        self.env.cr.execute("SELECT 1 FROM information_schema.tables WHERE table_name='mrp_workcenter_mold_rel'")
        if not self.env.cr.fetchone():
            return

        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    ROW_NUMBER() OVER () AS id,
                    m.id AS machine_id,
                    mold.id AS mold_id,
                    p.id AS product_id,
                    mold.mold_life_current AS mold_life_current,
                    mold.mold_life_limit AS mold_life_limit,
                    mold.mold_state AS mold_state,
                    line.cycle_time AS cycle_time,
                    line.units_per_hour AS units_per_hour
                FROM mrp_workcenter m
                JOIN mrp_workcenter_mold_rel rel_mold ON rel_mold.workcenter_id = m.id
                JOIN mrp_workcenter mold ON rel_mold.mold_id = mold.id
                JOIN mrp_mold_product_line line ON line.mold_id = mold.id
                JOIN product_product p ON line.product_id = p.id
                WHERE m.is_mold = false AND mold.is_mold = true
            )
        """
            % self._table
        )
