from odoo import models, fields, api


class PurchasePriceHistory(models.Model):
    _name = "purchase.price.history"
    _description = "Purchase Price History"
    _auto = False  # SQL view based model

    product_id = fields.Many2one("product.product", string="Product")
    partner_id = fields.Many2one("res.partner", string="Vendor")
    date_order = fields.Datetime(string="Order Date")
    currency_id = fields.Many2one("res.currency", string="Currency")
    price_unit = fields.Float(string="Unit Price")
    qty = fields.Float(string="Quantity")
    po_id = fields.Many2one("purchase.order", string="PO Reference")
    avg_price = fields.Float(string="Average Price", readonly=True)

    def init(self):
        """Create or replace SQL view for historical purchase prices."""
        self._cr.execute("""
            CREATE OR REPLACE VIEW purchase_price_history AS (
                SELECT
                    pol.id AS id,
                    pol.product_id AS product_id,
                    po.partner_id AS partner_id,
                    po.date_order AS date_order,
                    po.currency_id AS currency_id,
                    pol.price_unit AS price_unit,
                    pol.product_qty AS qty,
                    po.id AS po_id,
                    (
                        SELECT AVG(pol2.price_unit)
                        FROM purchase_order_line pol2
                        JOIN purchase_order po2 ON po2.id = pol2.order_id
                        WHERE pol2.product_id = pol.product_id
                          AND po2.state IN ('purchase','done')
                    ) AS avg_price
                FROM purchase_order_line pol
                JOIN purchase_order po ON pol.order_id = po.id
                WHERE po.state IN ('purchase','done')
            );
        """)


# -----------------------------
# Purchase Order
# -----------------------------
class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    price_history_count = fields.Integer(
        string="Price History Count",
        compute="_compute_price_history_count",
    )

    @api.depends("order_line.product_id")
    def _compute_price_history_count(self):
        history = self.env["purchase.price.history"]
        for rec in self:
            product_ids = rec.order_line.mapped("product_id").ids
            rec.price_history_count = history.search_count([
                ("product_id", "in", product_ids)
            ]) if product_ids else 0

    def action_open_price_history(self):
        self.ensure_one()
        product_ids = self.order_line.product_id.ids
        return {
            "type": "ir.actions.act_window",
            "name": "Price History",
            "res_model": "purchase.price.history",
            "view_mode": "list",
            "views": [(False, "list")],
            "target": "new",
            "domain": [("product_id", "in", product_ids)] if product_ids else [],
        }


# -----------------------------
# Purchase Request
# -----------------------------
class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    price_history_count = fields.Integer(
        string="Price History Count",
        compute="_compute_pr_price_history_count",
    )

    @api.depends("line_ids.product_id")
    def _compute_pr_price_history_count(self):
        history = self.env["purchase.price.history"]
        for rec in self:
            product_ids = rec.line_ids.mapped("product_id").ids
            rec.price_history_count = history.search_count([
                ("product_id", "in", product_ids)
            ]) if product_ids else 0

    def action_open_price_history(self):
        self.ensure_one()
        product_ids = self.line_ids.product_id.ids
        return {
            "type": "ir.actions.act_window",
            "name": "Price History",
            "res_model": "purchase.price.history",
            "view_mode": "list",
            "views": [(False, "list")],
            "target": "new",
            "domain": [("product_id", "in", product_ids)] if product_ids else [],
        }


# -----------------------------
# Purchase Order Line
# -----------------------------
class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    avg_purchase_price = fields.Float(
        string="Avg Price",
        compute="_compute_avg_purchase_price",
        store=False,
    )

    @api.depends("product_id")
    def _compute_avg_purchase_price(self):
        history = self.env["purchase.price.history"]
        for line in self:
            if not line.product_id:
                line.avg_purchase_price = 0
                continue
            history_rec = history.search(
                [("product_id", "=", line.product_id.id)],
                order="date_order DESC",
                limit=1
            )
            line.avg_purchase_price = history_rec.avg_price if history_rec else 0


# -----------------------------
# Purchase Request Line
# -----------------------------
class PurchaseRequestLine(models.Model):
    _inherit = "purchase.request.line"

    avg_purchase_price = fields.Float(
        string="Avg Price",
        compute="_compute_avg_purchase_price",
        store=False,
    )

    @api.depends("product_id")
    def _compute_avg_purchase_price(self):
        history = self.env["purchase.price.history"]
        for line in self:
            if not line.product_id:
                line.avg_purchase_price = 0
                continue
            history_rec = history.search(
                [("product_id", "=", line.product_id.id)],
                order="date_order DESC",
                limit=1
            )
            line.avg_purchase_price = history_rec.avg_price if history_rec else 0

