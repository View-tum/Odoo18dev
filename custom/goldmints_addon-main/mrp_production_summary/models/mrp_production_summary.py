from odoo import fields, models


class MrpProductionSummaryLine(models.Model):
    _name = "mrp.production.summary.line"
    _description = "MO Production Summary Line"
    _auto = False
    _order = "production_id desc, line_type_order asc, product_name asc"

    production_id = fields.Many2one("mrp.production", string="Manufacturing Order", readonly=True)
    production_state = fields.Selection(related="production_id.state", string="MO State", store=False)
    product_mo_id = fields.Many2one(related="production_id.product_id", string="MO Product", store=False)
    procurement_group_id = fields.Many2one("procurement.group", string="Backorder Group", readonly=True)

    line_type = fields.Selection(
        [
            ("product", "Finished Product"),
            ("component", "Component"),
            ("operation", "Operation"),
            ("employee", "Employee"),
            ("mold", "Mold"),
            ("scrap", "Scrapped Product"),
        ],
        string="Type",
        readonly=True,
    )
    line_type_order = fields.Integer(string="Sort Order", readonly=True)

    product_id = fields.Many2one("product.product", string="Product / Resource", readonly=True)
    product_name = fields.Char(string="Description", readonly=True)
    workcenter_id = fields.Many2one("mrp.workcenter", string="Work Center", readonly=True)

    planned_qty = fields.Float(string="Planned Qty", readonly=True, digits="Product Unit of Measure")
    actual_qty = fields.Float(string="Actual Qty", readonly=True, digits="Product Unit of Measure")
    uom_id = fields.Many2one("uom.uom", string="UoM", readonly=True)

    duration_expected = fields.Float(string="Expected Duration (min)", readonly=True)
    duration_actual = fields.Float(string="Actual Duration (min)", readonly=True)

    cost_estimated = fields.Float(string="Estimated Cost", readonly=True)
    cost_actual = fields.Float(string="Actual Cost", readonly=True)

    unit_cost_std = fields.Float(string="Std Unit Cost", readonly=True)
    unit_cost_actual = fields.Float(string="Actual Unit Cost", readonly=True)

    price_variance = fields.Float(string="Price Variance", readonly=True)
    usage_variance = fields.Float(string="Usage Variance", readonly=True)
    efficiency_variance = fields.Float(string="Efficiency Variance", readonly=True)
    rate_variance = fields.Float(string="Rate Variance", readonly=True)
    total_variance = fields.Float(string="Total Variance", readonly=True)
    lot_id = fields.Many2one("stock.lot", string="Lot/Serial", readonly=True)
    source_document = fields.Char(string="Source", readonly=True)
    source_vendor_id = fields.Many2one("res.partner", string="Source Vendor", readonly=True)
    source_mo_id = fields.Many2one("mrp.production", string="Source MO", readonly=True)

    mps_week_name = fields.Char(string="MPS Week", readonly=True)
    source_sale_order_id = fields.Many2one("sale.order", string="Source Sales Order", readonly=True)

    def _table_exists(self, table_name):
        self.env.cr.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_name = %s",
            (table_name,),
        )
        return bool(self.env.cr.fetchone())

    def init(self):
        self.env.cr.execute("DROP VIEW IF EXISTS %s CASCADE" % self._table)

        has_employee_cost = self._table_exists("mrp_production_employee_cost_line")
        has_mold = self._table_exists("mrp_workorder") and self.env.cr.execute(
            "SELECT 1 FROM information_schema.columns WHERE table_name='mrp_workorder' AND column_name='mold_cost'"
        ) or self.env.cr.fetchone()

        unions = [
            self._get_product_sql(),
            self._get_component_sql(),
            self._get_operation_sql(),
            self._get_scrap_sql(),
        ]

        if has_employee_cost:
            unions.append(self._get_employee_sql())
        if has_mold:
            unions.append(self._get_mold_sql())

        sql = " UNION ALL ".join(unions)
        self.env.cr.execute(
            "CREATE OR REPLACE VIEW %s AS (%s)" % (self._table, sql)
        )

    def _get_product_sql(self):
        return """
            SELECT
                sm.id AS id,
                sm.production_id AS production_id,
                mp.procurement_group_id AS procurement_group_id,
                'product' AS line_type,
                1 AS line_type_order,
                sm.product_id AS product_id,
                (pt.name->>'en_US')::text AS product_name,
                NULL::int AS workcenter_id,
                sm.product_uom_qty::float AS planned_qty,
                sm.quantity::float AS actual_qty,
                sm.product_uom AS uom_id,
                NULL::float AS duration_expected,
                NULL::float AS duration_actual,
                COALESCE(
                    sm.product_uom_qty
                    * COALESCE((pp.standard_price->>sm.company_id::text)::numeric, 0),
                    0
                )::float AS cost_estimated,
                COALESCE(svl_sum.total_value, 0)::float AS cost_actual,
                COALESCE((pp.standard_price->>sm.company_id::text)::numeric, 0)::float AS unit_cost_std,
                (COALESCE(svl_sum.total_value, 0) / NULLIF(sm.quantity, 0))::float AS unit_cost_actual,
                0.0::float AS price_variance,
                0.0::float AS usage_variance,
                0.0::float AS efficiency_variance,
                0.0::float AS rate_variance,
                (COALESCE(svl_sum.total_value, 0) - COALESCE(sm.product_uom_qty * (pp.standard_price->>sm.company_id::text)::numeric, 0))::float AS total_variance,
                sml_lot.lot_id AS lot_id,
                NULL::varchar AS source_document,
                NULL::int AS source_vendor_id,
                NULL::int AS source_mo_id,
                mp.mps_week_name::text AS mps_week_name,
                mp.source_sale_order_id AS source_sale_order_id
            FROM stock_move sm
            JOIN mrp_production mp ON mp.id = sm.production_id
            JOIN product_product pp ON pp.id = sm.product_id
            JOIN product_template pt ON pt.id = pp.product_tmpl_id
            LEFT JOIN (
                SELECT stock_move_id, ABS(SUM(value)) AS total_value
                FROM stock_valuation_layer GROUP BY stock_move_id
            ) svl_sum ON svl_sum.stock_move_id = sm.id
            LEFT JOIN (
                SELECT DISTINCT ON (move_id) move_id, lot_id
                FROM stock_move_line WHERE lot_id IS NOT NULL
                ORDER BY move_id, id
            ) sml_lot ON sml_lot.move_id = sm.id
            WHERE sm.production_id IS NOT NULL
                AND sm.state = 'done' AND sm.scrapped = FALSE
        """

    def _get_component_sql(self):
        return """
            SELECT
                sm.id + 100000000 AS id,
                sm.raw_material_production_id AS production_id,
                mp.procurement_group_id AS procurement_group_id,
                'component' AS line_type,
                2 AS line_type_order,
                sm.product_id AS product_id,
                (pt.name->>'en_US')::text AS product_name,
                NULL::int AS workcenter_id,
                sm.product_uom_qty::float AS planned_qty,
                sm.quantity::float AS actual_qty,
                sm.product_uom AS uom_id,
                NULL::float AS duration_expected,
                NULL::float AS duration_actual,
                COALESCE(
                    sm.product_uom_qty
                    * COALESCE((pp.standard_price->>sm.company_id::text)::numeric, 0),
                    0
                )::float AS cost_estimated,
                COALESCE(svl_sum.total_value, 0)::float AS cost_actual,
                COALESCE((pp.standard_price->>sm.company_id::text)::numeric, 0)::float AS unit_cost_std,
                (COALESCE(svl_sum.total_value, 0) / NULLIF(sm.quantity, 0))::float AS unit_cost_actual,
                ((COALESCE(svl_sum.total_value, 0) / NULLIF(sm.quantity, 0)) - COALESCE((pp.standard_price->>sm.company_id::text)::numeric, 0)) * sm.quantity::float AS price_variance,
                (sm.quantity - sm.product_uom_qty) * COALESCE((pp.standard_price->>sm.company_id::text)::numeric, 0)::float AS usage_variance,
                0.0::float AS efficiency_variance,
                0.0::float AS rate_variance,
                (COALESCE(svl_sum.total_value, 0) - COALESCE(sm.product_uom_qty * (pp.standard_price->>sm.company_id::text)::numeric, 0))::float AS total_variance,
                sml_lot.lot_id AS lot_id,
                COALESCE(
                    'PO: ' || po.name || ' (' || rp.name || ')',
                    'MO: ' || src_mo.name,
                    NULL
                )::text AS source_document,
                po_partner.partner_id AS source_vendor_id,
                src_mo.id AS source_mo_id,
                mp.mps_week_name::text AS mps_week_name,
                mp.source_sale_order_id AS source_sale_order_id
            FROM stock_move sm
            JOIN mrp_production mp ON mp.id = sm.raw_material_production_id
            JOIN product_product pp ON pp.id = sm.product_id
            JOIN product_template pt ON pt.id = pp.product_tmpl_id
            LEFT JOIN (
                SELECT stock_move_id, ABS(SUM(value)) AS total_value
                FROM stock_valuation_layer GROUP BY stock_move_id
            ) svl_sum ON svl_sum.stock_move_id = sm.id
            LEFT JOIN (
                SELECT DISTINCT ON (move_id) move_id, lot_id
                FROM stock_move_line WHERE lot_id IS NOT NULL
                ORDER BY move_id, id
            ) sml_lot ON sml_lot.move_id = sm.id
            LEFT JOIN (
                SELECT DISTINCT ON (sml_r.lot_id)
                    sml_r.lot_id, po.id AS po_id, po.name AS po_name, po.partner_id
                FROM stock_move_line sml_r
                JOIN stock_move sm_r ON sm_r.id = sml_r.move_id
                JOIN stock_picking sp ON sp.id = sm_r.picking_id
                JOIN stock_picking_type spt ON spt.id = sp.picking_type_id
                JOIN purchase_order_line pol ON pol.id = sm_r.purchase_line_id
                JOIN purchase_order po ON po.id = pol.order_id
                WHERE sml_r.lot_id IS NOT NULL AND spt.code = 'incoming'
                ORDER BY sml_r.lot_id, sml_r.id
            ) po_partner ON po_partner.lot_id = sml_lot.lot_id
            LEFT JOIN purchase_order po ON po.id = po_partner.po_id
            LEFT JOIN res_partner rp ON rp.id = po_partner.partner_id
            LEFT JOIN (
                SELECT DISTINCT ON (sml_p.lot_id)
                    sml_p.lot_id, mp.id, mp.name
                FROM stock_move_line sml_p
                JOIN stock_move sm_p ON sm_p.id = sml_p.move_id
                JOIN mrp_production mp ON mp.id = sm_p.production_id
                WHERE sml_p.lot_id IS NOT NULL AND sm_p.production_id IS NOT NULL
                ORDER BY sml_p.lot_id, sml_p.id
            ) src_mo ON src_mo.lot_id = sml_lot.lot_id
            WHERE sm.raw_material_production_id IS NOT NULL
                AND sm.state = 'done' AND sm.scrapped = FALSE
        """

    def _get_operation_sql(self):
        return """
            SELECT
                wo.id + 200000000 AS id,
                wo.production_id AS production_id,
                mp.procurement_group_id AS procurement_group_id,
                'operation' AS line_type,
                3 AS line_type_order,
                NULL::int AS product_id,
                wo.name::text AS product_name,
                wo.workcenter_id AS workcenter_id,
                NULL::float AS planned_qty,
                NULL::float AS actual_qty,
                NULL::int AS uom_id,
                wo.duration_expected::float AS duration_expected,
                wo.duration::float AS duration_actual,
                ROUND(CAST(wo.duration_expected / 60.0 * wc.costs_hour AS numeric), 2)::float AS cost_estimated,
                ROUND(CAST(wo.duration / 60.0 * wc.costs_hour AS numeric), 2)::float AS cost_actual,
                wc.costs_hour::float AS unit_cost_std,
                wc.costs_hour::float AS unit_cost_actual,
                0.0::float AS price_variance,
                0.0::float AS usage_variance,
                (ROUND(CAST(wo.duration / 60.0 * wc.costs_hour AS numeric), 2) - ROUND(CAST(wo.duration_expected / 60.0 * wc.costs_hour AS numeric), 2))::float AS efficiency_variance,
                0.0::float AS rate_variance,
                (ROUND(CAST(wo.duration / 60.0 * wc.costs_hour AS numeric), 2) - ROUND(CAST(wo.duration_expected / 60.0 * wc.costs_hour AS numeric), 2))::float AS total_variance,
                NULL::int AS lot_id,
                wc.name::text AS source_document,
                NULL::int AS source_vendor_id,
                NULL::int AS source_mo_id,
                mp.mps_week_name::text AS mps_week_name,
                mp.source_sale_order_id AS source_sale_order_id
            FROM mrp_workorder wo
            JOIN mrp_production mp ON mp.id = wo.production_id
            JOIN mrp_workcenter wc ON wc.id = wo.workcenter_id
            WHERE wo.state = 'done'
        """

    def _get_employee_sql(self):
        return """
            SELECT
                ecl.id + 300000000 AS id,
                ecl.production_id AS production_id,
                mp.procurement_group_id AS procurement_group_id,
                'employee' AS line_type,
                4 AS line_type_order,
                NULL::int AS product_id,
                COALESCE(emp.name, 'Employee')::text AS product_name,
                ecl.workcenter_id AS workcenter_id,
                NULL::float AS planned_qty,
                NULL::float AS actual_qty,
                NULL::int AS uom_id,
                COALESCE(wo_agg.total_expected / NULLIF(emp_cnt.emp_count, 0), 0)::float AS duration_expected,
                (ecl.duration_hours * 60)::float AS duration_actual,
                ROUND(CAST(
                    COALESCE(wo_agg.total_expected / NULLIF(emp_cnt.emp_count, 0), 0)
                    / 60.0 * ecl.hourly_rate AS numeric
                ), 2)::float AS cost_estimated,
                ecl.cost::float AS cost_actual,
                ecl.hourly_rate::float AS unit_cost_std,
                ecl.hourly_rate::float AS unit_cost_actual,
                0.0::float AS price_variance,
                0.0::float AS usage_variance,
                (ecl.cost - ROUND(CAST(COALESCE(wo_agg.total_expected / NULLIF(emp_cnt.emp_count, 0), 0) / 60.0 * ecl.hourly_rate AS numeric), 2))::float AS efficiency_variance,
                0.0::float AS rate_variance,
                (ecl.cost - ROUND(CAST(COALESCE(wo_agg.total_expected / NULLIF(emp_cnt.emp_count, 0), 0) / 60.0 * ecl.hourly_rate AS numeric), 2))::float AS total_variance,
                NULL::int AS lot_id,
                COALESCE(emp.name, 'Employee')::text AS source_document,
                NULL::int AS source_vendor_id,
                NULL::int AS source_mo_id,
                mp.mps_week_name::text AS mps_week_name,
                mp.source_sale_order_id AS source_sale_order_id
            FROM mrp_production_employee_cost_line ecl
            JOIN mrp_production mp ON mp.id = ecl.production_id
            LEFT JOIN hr_employee emp ON emp.id = ecl.employee_id
            LEFT JOIN (
                SELECT production_id, SUM(duration_expected) AS total_expected
                FROM mrp_workorder
                GROUP BY production_id
            ) wo_agg ON wo_agg.production_id = ecl.production_id
            LEFT JOIN (
                SELECT production_id, COUNT(DISTINCT employee_id) AS emp_count
                FROM mrp_production_employee_cost_line
                WHERE employee_id IS NOT NULL
                GROUP BY production_id
            ) emp_cnt ON emp_cnt.production_id = ecl.production_id
        """

    def _get_mold_sql(self):
        return """
            SELECT
                wo.id + 400000000 AS id,
                wo.production_id AS production_id,
                mp.procurement_group_id AS procurement_group_id,
                'mold' AS line_type,
                5 AS line_type_order,
                NULL::int AS product_id,
                COALESCE(wo.mold_names, wo.name || ' (Mold)')::text AS product_name,
                wo.workcenter_id AS workcenter_id,
                NULL::float AS planned_qty,
                NULL::float AS actual_qty,
                NULL::int AS uom_id,
                wo.duration_expected::float AS duration_expected,
                wo.duration::float AS duration_actual,
                -- Estimated Cost: Expected Duration * Combined Mold Rate
                (wo.duration_expected / 60.0 * COALESCE(mold_rate.total_rate, 0))::float AS cost_estimated,
                COALESCE(wo.mold_cost, 0)::float AS cost_actual,
                COALESCE(mold_rate.total_rate, 0)::float AS unit_cost_std,
                COALESCE(mold_rate.total_rate, 0)::float AS unit_cost_actual,
                0.0::float AS price_variance,
                0.0::float AS usage_variance,
                -- Efficiency Variance: (Actual Duration - Expected Duration) / 60 * Rate
                ((wo.duration - wo.duration_expected) / 60.0 * COALESCE(mold_rate.total_rate, 0))::float AS efficiency_variance,
                0.0::float AS rate_variance,
                (COALESCE(wo.mold_cost, 0) - (wo.duration_expected / 60.0 * COALESCE(mold_rate.total_rate, 0)))::float AS total_variance,
                NULL::int AS lot_id,
                wo.mold_names::text AS source_document,
                NULL::int AS source_vendor_id,
                NULL::int AS source_mo_id,
                mp.mps_week_name::text AS mps_week_name,
                mp.source_sale_order_id AS source_sale_order_id
            FROM mrp_workorder wo
            JOIN mrp_production mp ON mp.id = wo.production_id
            LEFT JOIN (
                SELECT rel.mrp_workorder_id, SUM(wc.mold_cost_hour) AS total_rate
                FROM mrp_workcenter_mrp_workorder_rel rel
                JOIN mrp_workcenter wc ON wc.id = rel.mrp_workcenter_id
                GROUP BY rel.mrp_workorder_id
            ) mold_rate ON mold_rate.mrp_workorder_id = wo.id
            WHERE wo.state = 'done' AND (wo.mold_cost > 0 OR wo.duration_expected > 0)
        """

    def _get_scrap_sql(self):
        """
        Fetch scrap records linked to the MO.
        We capture scrap in two ways:
        1. Direct Link: sc.production_id (Where the scrap happened)
        2. Lot Traceability: sc.lot_id -> MO that produced it (Allocation Back)
        """
        return """
            SELECT
                sc.id + 500000000 AS id,
                sc.production_id AS production_id,
                mp.procurement_group_id AS procurement_group_id,
                'scrap' AS line_type,
                6 AS line_type_order,
                sc.product_id AS product_id,
                (pt.name->>'en_US')::text AS product_name,
                NULL::int AS workcenter_id,
                NULL::float AS planned_qty,
                sc.scrap_qty::float AS actual_qty,
                sc.product_uom_id AS uom_id,
                NULL::float AS duration_expected,
                NULL::float AS duration_actual,
                NULL::float AS cost_estimated,
                COALESCE(svl_sum.total_value, 0)::float AS cost_actual,
                0.0::float AS unit_cost_std,
                0.0::float AS unit_cost_actual,
                0.0::float AS price_variance,
                0.0::float AS usage_variance,
                0.0::float AS efficiency_variance,
                0.0::float AS rate_variance,
                COALESCE(svl_sum.total_value, 0)::float AS total_variance,
                sc.lot_id AS lot_id,
                ('Scrap: ' || sc.name)::text AS source_document,
                NULL::int AS source_vendor_id,
                NULL::int AS source_mo_id,
                mp.mps_week_name::text AS mps_week_name,
                mp.source_sale_order_id AS source_sale_order_id
            FROM stock_scrap sc
            JOIN mrp_production mp ON mp.id = sc.production_id
            JOIN product_product pp ON pp.id = sc.product_id
            JOIN product_template pt ON pt.id = pp.product_tmpl_id
            LEFT JOIN (
                SELECT sm.scrap_id, ABS(SUM(svl.value)) AS total_value
                FROM stock_valuation_layer svl
                JOIN stock_move sm ON sm.id = svl.stock_move_id
                WHERE sm.scrap_id IS NOT NULL
                GROUP BY sm.scrap_id
            ) svl_sum ON svl_sum.scrap_id = sc.id
            WHERE sc.production_id IS NOT NULL AND sc.state = 'done'

            UNION ALL

            -- Allocation Back: Link scrap to the MO that produced the Lot
            SELECT
                sc.id + 600000000 AS id,
                src_mo.id AS production_id,
                src_mo.procurement_group_id AS procurement_group_id,
                'scrap' AS line_type,
                6 AS line_type_order,
                sc.product_id AS product_id,
                (pt.name->>'en_US')::text AS product_name,
                NULL::int AS workcenter_id,
                NULL::float AS planned_qty,
                sc.scrap_qty::float AS actual_qty,
                sc.product_uom_id AS uom_id,
                NULL::float AS duration_expected,
                NULL::float AS duration_actual,
                NULL::float AS cost_estimated,
                COALESCE(svl_sum.total_value, 0)::float AS cost_actual,
                0.0::float AS unit_cost_std,
                0.0::float AS unit_cost_actual,
                0.0::float AS price_variance,
                0.0::float AS usage_variance,
                0.0::float AS efficiency_variance,
                0.0::float AS rate_variance,
                COALESCE(svl_sum.total_value, 0)::float AS total_variance,
                sc.lot_id AS lot_id,
                ('Scrap (Allocated): ' || sc.name)::text AS source_document,
                NULL::int AS source_vendor_id,
                NULL::int AS source_mo_id,
                src_mo.mps_week_name::text AS mps_week_name,
                src_mo.source_sale_order_id AS source_sale_order_id
            FROM stock_scrap sc
            JOIN stock_move_line sml ON sml.lot_id = sc.lot_id
            JOIN stock_move sm ON sm.id = sml.move_id
            JOIN mrp_production src_mo ON src_mo.id = sm.production_id
            JOIN product_product pp ON pp.id = sc.product_id
            JOIN product_template pt ON pt.id = pp.product_tmpl_id
            LEFT JOIN (
                SELECT sm_v.scrap_id, ABS(SUM(svl.value)) AS total_value
                FROM stock_valuation_layer svl
                JOIN stock_move sm_v ON sm_v.id = svl.stock_move_id
                WHERE sm_v.scrap_id IS NOT NULL
                GROUP BY sm_v.scrap_id
            ) svl_sum ON svl_sum.scrap_id = sc.id
            WHERE sc.lot_id IS NOT NULL
              AND sm.production_id IS NOT NULL
              AND sc.state = 'done'
              -- Avoid double counting if it's the same MO
              AND (sc.production_id IS NULL OR sc.production_id != src_mo.id)
        """

class MrpReport(models.Model):
    _inherit = 'mrp.report'

    mps_week_name = fields.Char("MPS Week", readonly=True)
    source_sale_order_id = fields.Many2one('sale.order', "Source Sales Order", readonly=True)

    def _select(self):
        return super()._select() + ", mo.mps_week_name::text AS mps_week_name, mo.source_sale_order_id AS source_sale_order_id"

    def _group_by(self):
        return super()._group_by() + ", mo.mps_week_name, mo.source_sale_order_id"


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    mps_week_name = fields.Char(string="MPS Week")
    source_sale_order_id = fields.Many2one('sale.order', string="Source Sales Order")

    production_summary_line_ids = fields.One2many(
        "mrp.production.summary.line",
        "production_id",
        string="Production Summary Lines",
        readonly=True,
    )

    total_cost_actual = fields.Float(
        string="Total Actual Cost",
        compute="_compute_mo_total_costs",
        store=False,
    )
    total_cost_estimated = fields.Float(
        string="Total Estimated Cost",
        compute="_compute_mo_total_costs",
        store=False,
    )
    has_cost_overrun = fields.Boolean(
        string="Cost Overrun",
        compute="_compute_mo_total_costs",
        store=False,
    )

    cost_variance = fields.Float(
        string="Variance",
        compute="_compute_mo_total_costs",
        store=False,
    )
    cost_health = fields.Selection([
        ('underrun', 'Underrun (Saving)'),
        ('normal', 'Normal'),
        ('overrun', 'Overrun (Deficit)')
    ],
        string="Cost Health",
        compute="_compute_mo_total_costs",
        store=False,
    )

    def _compute_mo_total_costs(self):
        for mo in self:
            total_actual = sum(mo.production_summary_line_ids.filtered(lambda line: line.line_type != 'product').mapped('cost_actual'))
            total_estimated = sum(mo.production_summary_line_ids.filtered(lambda line: line.line_type != 'product').mapped('cost_estimated'))
            variance = total_actual - total_estimated
            
            mo.total_cost_actual = total_actual
            mo.total_cost_estimated = total_estimated
            mo.cost_variance = variance
            
            if total_estimated == 0:
                mo.cost_health = 'normal'
                mo.has_cost_overrun = False
            elif variance > 0.01:
                mo.cost_health = 'overrun'
                mo.has_cost_overrun = True
            elif variance < -0.01:
                mo.cost_health = 'underrun'
                mo.has_cost_overrun = False
            else:
                mo.cost_health = 'normal'
                mo.has_cost_overrun = False

    def action_view_cost_breakdown(self):
        self.ensure_one()
        return {
            'name': 'Cost Details: %s' % self.name,
            'view_mode': 'list',
            'res_model': 'mrp.production.summary.line',
            'domain': [('production_id', '=', self.id)],
            'context': {'search_default_group_type': 1},
            'type': 'ir.actions.act_window',
            'target': 'current',
        }

    current_mo_duration_expected = fields.Float(
        string="Expected Duration",
        compute="_compute_mo_duration_expected",
        store=False,
        help="Total expected duration for this specific Manufacturing Order in hours."
    )
    
    hierarchy_duration_expected = fields.Float(
        string="Total Expected Duration",
        compute="_compute_mo_duration_expected",
        store=False,
        help="Total expected duration for this MO and all its child sub-assemblies in days (based on Odoo working hours)."
    )

    def _compute_mo_duration_expected(self):
        for mo in self:
            # 1. Calculate time for THIS specific MO (in minutes)
            # Handle parallel work orders: group by operation_id and take the max duration
            op_durations = {}
            for wo in mo.workorder_ids:
                key = wo.operation_id.id if wo.operation_id else wo.name
                if key not in op_durations or wo.duration_expected > op_durations[key]:
                    op_durations[key] = wo.duration_expected
            
            current_duration_mins = sum(op_durations.values())
            mo.current_mo_duration_expected = current_duration_mins
            
            # 2. Hierarchy traversal to find all child MOs
            hierarchy_mos = mo._get_all_hierarchy_mos()
            
            # 3. Aggregate total expected time across all MOs in hierarchy
            total_hierarchy_mins = 0.0
            for child_mo in hierarchy_mos:
                child_op_durations = {}
                for wo in child_mo.workorder_ids:
                    key = wo.operation_id.id if wo.operation_id else wo.name
                    if key not in child_op_durations or wo.duration_expected > child_op_durations[key]:
                        child_op_durations[key] = wo.duration_expected
                total_hierarchy_mins += sum(child_op_durations.values())
            
            # 4. Calculate days based on working hours per day (fallback to 8.0)
            hours_per_day = mo.company_id.resource_calendar_id.hours_per_day or 8.0
            mo.hierarchy_duration_expected = (total_hierarchy_mins / 60.0) / hours_per_day
            
    def _get_all_hierarchy_mos(self, seen_mos=None):
        """
        Recursively find all child MOs linked via MTO (move_raw_ids.created_production_id)
        """
        self.ensure_one()
        if seen_mos is None:
            seen_mos = self.env['mrp.production']
            
        if self in seen_mos:
            return seen_mos
            
        seen_mos |= self
        
        # Find child MOs generated to fulfill the raw materials for this MO
        child_mos = self.move_raw_ids.mapped('created_production_id')
        for child_mo in child_mos:
            if child_mo and child_mo not in seen_mos:
                seen_mos = child_mo._get_all_hierarchy_mos(seen_mos)
                
        return seen_mos
