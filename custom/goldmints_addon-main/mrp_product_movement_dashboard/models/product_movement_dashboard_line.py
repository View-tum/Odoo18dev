from datetime import datetime, time

from odoo import _, api, fields, models


class ProductMovementDashboardLine(models.Model):
    _name = "product.movement.dashboard.line"
    _description = "Product Movement Dashboard Line"
    _order = "report_group_id, warehouse_id, default_code, product_id"

    batch_id = fields.Many2one(
        "product.movement.dashboard.batch",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one("res.company", required=True, index=True)
    warehouse_id = fields.Many2one("stock.warehouse", required=True, index=True)
    report_group_id = fields.Many2one("product.report.group", index=True)
    product_id = fields.Many2one("product.product", required=True, index=True)
    product_tmpl_id = fields.Many2one("product.template", related="product_id.product_tmpl_id", store=True)
    categ_id = fields.Many2one("product.category", related="product_id.categ_id", store=True)
    default_code = fields.Char(related="product_id.default_code", store=True)
    uom_id = fields.Many2one("uom.uom", related="product_id.uom_id", store=True)
    manufacturing_type = fields.Char(string="Manufacturing Type")

    produced_qty = fields.Float(string="Produced Qty", digits="Product Unit of Measure")
    received_qty = fields.Float(string="Received Qty", digits="Product Unit of Measure")
    issued_qty = fields.Float(string="Issued Qty", digits="Product Unit of Measure")
    net_movement_qty = fields.Float(
        string="Net Movement Qty",
        compute="_compute_status_fields",
        store=True,
        digits="Product Unit of Measure",
    )
    on_hand_qty = fields.Float(string="On Hand Qty", digits="Product Unit of Measure")
    min_qty = fields.Float(string="Min Qty", digits="Product Unit of Measure")
    max_qty = fields.Float(string="Max Qty", digits="Product Unit of Measure")

    below_min = fields.Boolean(string="Below Min", compute="_compute_status_fields", store=True)
    above_max = fields.Boolean(string="Above Max", compute="_compute_status_fields", store=True)
    shortage_qty = fields.Float(
        string="Shortage Qty",
        compute="_compute_status_fields",
        store=True,
        digits="Product Unit of Measure",
    )
    excess_qty = fields.Float(
        string="Excess Qty",
        compute="_compute_status_fields",
        store=True,
        digits="Product Unit of Measure",
    )

    @api.depends("produced_qty", "received_qty", "issued_qty", "on_hand_qty", "min_qty", "max_qty")
    def _compute_status_fields(self):
        for line in self:
            line.net_movement_qty = (line.produced_qty or 0.0) + (line.received_qty or 0.0) - (line.issued_qty or 0.0)
            line.below_min = bool(line.min_qty and line.on_hand_qty < line.min_qty)
            line.above_max = bool(line.max_qty and line.max_qty > 0 and line.on_hand_qty > line.max_qty)
            line.shortage_qty = max((line.min_qty or 0.0) - (line.on_hand_qty or 0.0), 0.0)
            line.excess_qty = max((line.on_hand_qty or 0.0) - (line.max_qty or 0.0), 0.0) if line.max_qty else 0.0

    def _get_internal_location_ids(self):
        self.ensure_one()
        return self.env["stock.location"].search(
            [("id", "child_of", self.warehouse_id.view_location_id.id), ("usage", "=", "internal")]
        ).ids

    def _get_batch_date_domain(self):
        self.ensure_one()
        date_from_dt = datetime.combine(self.batch_id.date_from, time.min)
        date_to_dt = datetime.combine(self.batch_id.date_to, time.max)
        return [
            ("date", ">=", fields.Datetime.to_string(date_from_dt)),
            ("date", "<=", fields.Datetime.to_string(date_to_dt)),
        ]

    def action_open_product(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.product_id.display_name,
            "res_model": "product.product",
            "res_id": self.product_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_open_stock_moves(self):
        self.ensure_one()
        internal_location_ids = self._get_internal_location_ids()
        domain = [
            ("product_id", "=", self.product_id.id),
            ("company_id", "=", self.company_id.id),
            ("state", "=", "done"),
            "|",
            ("location_id", "in", internal_location_ids),
            ("location_dest_id", "in", internal_location_ids),
        ] + self._get_batch_date_domain()
        return {
            "type": "ir.actions.act_window",
            "name": _("Stock Moves"),
            "res_model": "stock.move",
            "view_mode": "list,form",
            "domain": domain,
            "target": "current",
        }

    def action_open_production_moves(self):
        self.ensure_one()
        internal_location_ids = self._get_internal_location_ids()
        domain = [
            ("product_id", "=", self.product_id.id),
            ("company_id", "=", self.company_id.id),
            ("state", "=", "done"),
            "|",
            ("location_id.usage", "=", "production"),
            ("location_dest_id.usage", "=", "production"),
            "|",
            ("location_id", "in", internal_location_ids),
            ("location_dest_id", "in", internal_location_ids),
        ] + self._get_batch_date_domain()
        return {
            "type": "ir.actions.act_window",
            "name": _("Production Moves"),
            "res_model": "stock.move",
            "view_mode": "list,form",
            "domain": domain,
            "target": "current",
        }

    def action_open_reordering_rules(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Reordering Rules"),
            "res_model": "stock.warehouse.orderpoint",
            "view_mode": "list,form",
            "domain": [
                ("product_id", "=", self.product_id.id),
                ("warehouse_id", "=", self.warehouse_id.id),
            ],
            "target": "current",
        }
