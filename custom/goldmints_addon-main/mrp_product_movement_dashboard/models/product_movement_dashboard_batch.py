from collections import defaultdict
from datetime import datetime, time

from odoo import _, api, fields, models


class ProductMovementDashboardBatch(models.Model):
    _name = "product.movement.dashboard.batch"
    _description = "Product Movement Dashboard Batch"
    _order = "id desc"

    name = fields.Char(default=lambda self: _("New"), copy=False, readonly=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    date_from = fields.Date(required=True, default=lambda self: fields.Date.context_today(self).replace(day=1))
    date_to = fields.Date(required=True, default=lambda self: fields.Date.context_today(self))
    warehouse_ids = fields.Many2many(
        "stock.warehouse",
        "product_movement_dashboard_batch_warehouse_rel",
        "batch_id",
        "warehouse_id",
        string="Warehouses",
    )
    state = fields.Selection(
        [("draft", "Draft"), ("generated", "Generated")],
        default="draft",
        required=True,
    )
    line_ids = fields.One2many("product.movement.dashboard.line", "batch_id", string="Lines")

    line_count = fields.Integer(compute="_compute_counters")
    product_count = fields.Integer(compute="_compute_counters")
    report_group_count = fields.Integer(compute="_compute_counters")
    below_min_count = fields.Integer(compute="_compute_counters")
    above_max_count = fields.Integer(compute="_compute_counters")

    total_produced_qty = fields.Float(compute="_compute_totals", digits="Product Unit of Measure")
    total_received_qty = fields.Float(compute="_compute_totals", digits="Product Unit of Measure")
    total_issued_qty = fields.Float(compute="_compute_totals", digits="Product Unit of Measure")
    total_net_movement_qty = fields.Float(compute="_compute_totals", digits="Product Unit of Measure")
    total_on_hand_qty = fields.Float(compute="_compute_totals", digits="Product Unit of Measure")
    total_shortage_qty = fields.Float(compute="_compute_totals", digits="Product Unit of Measure")
    total_excess_qty = fields.Float(compute="_compute_totals", digits="Product Unit of Measure")

    @api.depends("line_ids", "line_ids.product_id", "line_ids.report_group_id", "line_ids.below_min", "line_ids.above_max")
    def _compute_counters(self):
        for batch in self:
            batch.line_count = len(batch.line_ids)
            batch.product_count = len(batch.line_ids.mapped("product_id"))
            batch.report_group_count = len(batch.line_ids.mapped("report_group_id"))
            batch.below_min_count = len(batch.line_ids.filtered("below_min"))
            batch.above_max_count = len(batch.line_ids.filtered("above_max"))

    @api.depends(
        "line_ids.produced_qty",
        "line_ids.received_qty",
        "line_ids.issued_qty",
        "line_ids.net_movement_qty",
        "line_ids.on_hand_qty",
        "line_ids.shortage_qty",
        "line_ids.excess_qty",
    )
    def _compute_totals(self):
        for batch in self:
            batch.total_produced_qty = sum(batch.line_ids.mapped("produced_qty"))
            batch.total_received_qty = sum(batch.line_ids.mapped("received_qty"))
            batch.total_issued_qty = sum(batch.line_ids.mapped("issued_qty"))
            batch.total_net_movement_qty = sum(batch.line_ids.mapped("net_movement_qty"))
            batch.total_on_hand_qty = sum(batch.line_ids.mapped("on_hand_qty"))
            batch.total_shortage_qty = sum(batch.line_ids.mapped("shortage_qty"))
            batch.total_excess_qty = sum(batch.line_ids.mapped("excess_qty"))

    @api.model_create_multi
    def create(self, vals_list):
        seq_model = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = seq_model.next_by_code("product.movement.dashboard.batch") or _("New")
        return super().create(vals_list)

    def action_reset(self):
        for batch in self:
            batch.line_ids.unlink()
            batch.state = "draft"
        return True

    def action_generate_lines(self):
        self.ensure_one()
        self.line_ids.unlink()

        warehouses = self.warehouse_ids
        if not warehouses:
            warehouses = self.env["stock.warehouse"].search([("company_id", "=", self.company_id.id)])

        date_from_dt = datetime.combine(self.date_from, time.min)
        date_to_dt = datetime.combine(self.date_to, time.max)

        line_vals = []
        for warehouse in warehouses:
            metrics = self._collect_warehouse_metrics(warehouse, date_from_dt, date_to_dt)
            products = self.env["product.product"].browse(list(metrics)).exists()
            product_map = {product.id: product for product in products if self._include_product_in_dashboard(product)}
            for product_id, values in metrics.items():
                product = product_map.get(product_id)
                if not product:
                    continue
                tmpl = product.product_tmpl_id
                manufacturing_type = False
                if "manufacturing_type" in tmpl._fields:
                    manufacturing_type = tmpl.manufacturing_type or False
                line_vals.append(
                    {
                        "batch_id": self.id,
                        "company_id": self.company_id.id,
                        "warehouse_id": warehouse.id,
                        "report_group_id": tmpl.report_group_id.id,
                        "product_id": product.id,
                        "manufacturing_type": manufacturing_type,
                        "produced_qty": values["produced_qty"],
                        "received_qty": values["received_qty"],
                        "issued_qty": values["issued_qty"],
                        "on_hand_qty": values["on_hand_qty"],
                        "min_qty": values["min_qty"],
                        "max_qty": values["max_qty"],
                    }
                )

        if line_vals:
            self.env["product.movement.dashboard.line"].create(line_vals)

        self.state = "generated"
        return self.action_open_lines_tree()

    def _include_product_in_dashboard(self, product):
        product_type = False
        if "detailed_type" in product._fields:
            product_type = product.detailed_type
        elif "type" in product._fields:
            product_type = product.type
        return product_type != "service"

    def _collect_warehouse_metrics(self, warehouse, date_from_dt, date_to_dt):
        metrics = defaultdict(
            lambda: {
                "produced_qty": 0.0,
                "received_qty": 0.0,
                "issued_qty": 0.0,
                "on_hand_qty": 0.0,
                "min_qty": 0.0,
                "max_qty": 0.0,
            }
        )

        internal_locations = self.env["stock.location"].search(
            [("id", "child_of", warehouse.view_location_id.id), ("usage", "=", "internal")]
        )
        internal_location_ids = internal_locations.ids
        if not internal_location_ids:
            return metrics

        quant_groups = self.env["stock.quant"].read_group(
            [
                ("company_id", "=", self.company_id.id),
                ("location_id", "in", internal_location_ids),
            ],
            ["product_id", "quantity:sum"],
            ["product_id"],
        )
        for row in quant_groups:
            if row.get("product_id"):
                metrics[row["product_id"][0]]["on_hand_qty"] = row.get("quantity", 0.0)

        orderpoints = self.env["stock.warehouse.orderpoint"].search([("warehouse_id", "=", warehouse.id)])
        for op in orderpoints:
            if self._include_product_in_dashboard(op.product_id):
                metrics[op.product_id.id]["min_qty"] += op.product_min_qty or 0.0
                metrics[op.product_id.id]["max_qty"] += op.product_max_qty or 0.0

        move_domain = [
            ("company_id", "=", self.company_id.id),
            ("state", "=", "done"),
            ("date", ">=", fields.Datetime.to_string(date_from_dt)),
            ("date", "<=", fields.Datetime.to_string(date_to_dt)),
            "|",
            ("location_id", "in", internal_location_ids),
            ("location_dest_id", "in", internal_location_ids),
        ]
        internal_location_ids_set = set(internal_location_ids)
        for move in self.env["stock.move"].search(move_domain):
            product = move.product_id
            if not product or not self._include_product_in_dashboard(product):
                continue

            qty = move.quantity or 0.0
            source_usage = move.location_id.usage
            dest_usage = move.location_dest_id.usage
            source_internal = move.location_id.id in internal_location_ids_set
            dest_internal = move.location_dest_id.id in internal_location_ids_set

            if dest_internal and source_usage == "production":
                metrics[product.id]["produced_qty"] += qty
            elif dest_internal and source_usage in {"supplier", "customer", "inventory", "transit"}:
                metrics[product.id]["received_qty"] += qty

            if source_internal and dest_usage == "customer":
                metrics[product.id]["issued_qty"] += qty

        return metrics

    def _build_line_action(self, name, view_mode="list,pivot,graph", extra_domain=None, extra_context=None):
        self.ensure_one()
        domain = [("batch_id", "=", self.id)]
        if extra_domain:
            domain += extra_domain
        context = {"search_default_group_by_report_group": 1}
        if extra_context:
            context.update(extra_context)
        return {
            "type": "ir.actions.act_window",
            "name": name,
            "res_model": "product.movement.dashboard.line",
            "view_mode": view_mode,
            "domain": domain,
            "context": context,
        }

    def action_open_lines_tree(self):
        self.ensure_one()
        return self._build_line_action(_("Product Movement Lines"), view_mode="list,pivot,graph")

    def action_open_lines_pivot(self):
        self.ensure_one()
        return self._build_line_action(_("Product Movement Pivot"), view_mode="pivot,list,graph")

    def action_open_lines_graph(self):
        self.ensure_one()
        return self._build_line_action(_("Product Movement Graph"), view_mode="graph,pivot,list")

    def action_open_below_min_lines(self):
        self.ensure_one()
        return self._build_line_action(
            _("Below Min Products"),
            view_mode="list,pivot,graph",
            extra_domain=[("below_min", "=", True)],
        )

    def action_open_above_max_lines(self):
        self.ensure_one()
        return self._build_line_action(
            _("Above Max Products"),
            view_mode="list,pivot,graph",
            extra_domain=[("above_max", "=", True)],
        )
