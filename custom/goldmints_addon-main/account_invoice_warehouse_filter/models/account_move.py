from odoo import api, fields, models

class AccountMove(models.Model):
    _inherit = "account.move"

    warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Warehouse",
        compute="_compute_warehouse_id",
        store=True,
        readonly=False,
        precompute=True,
        index=True,
    )

    @api.depends(
        "invoice_line_ids.sale_line_ids.order_id.warehouse_id",
        "invoice_line_ids.purchase_line_id.order_id.picking_type_id.warehouse_id",
        "invoice_origin",
    )
    def _compute_warehouse_id(self):
        for move in self:
            warehouse = False
            so_warehouses = move.invoice_line_ids.sale_line_ids.order_id.warehouse_id
            if so_warehouses:
                warehouse = so_warehouses[0]
            else:
                po_warehouses = move.invoice_line_ids.purchase_line_id.order_id.picking_type_id.warehouse_id
                if po_warehouses:
                    warehouse = po_warehouses[0]

            if not warehouse and move.invoice_origin:
                sale_order = self.env["sale.order"].search([("name", "=", move.invoice_origin)], limit=1)
                if sale_order and sale_order.warehouse_id:
                    warehouse = sale_order.warehouse_id
                else:
                    purchase_order = self.env["purchase.order"].search([("name", "=", move.invoice_origin)], limit=1)
                    if purchase_order and purchase_order.picking_type_id.warehouse_id:
                        warehouse = purchase_order.picking_type_id.warehouse_id

            if not warehouse and move.warehouse_id:
                continue

            move.warehouse_id = warehouse
