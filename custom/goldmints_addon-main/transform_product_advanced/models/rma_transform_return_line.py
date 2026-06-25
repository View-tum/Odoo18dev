from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare

class RMATransformReturnLine(models.Model):
    _name = "rma.transform.return.line"
    _description = "RMA Transform Return Line"

    rma_transform_return_id = fields.Many2one("rma.transform.return", string="Transform Return", required=True, ondelete="cascade")
    
    # Traceability
    original_delivery_id = fields.Many2one("stock.picking", string="Original Delivery", required=True)
    original_lot_id = fields.Many2one("stock.lot", string="Original Lot")
    original_delivery_line_id = fields.Many2one("stock.move.line", string="Original Delivery Line")
    partner_id = fields.Many2one("res.partner", related="rma_transform_return_id.partner_id", store=True)
    sale_order_id = fields.Many2one("sale.order", string="Sale Order")
    sale_line_id = fields.Many2one("sale.order.line", string="Sale Line")
    invoice_id = fields.Many2one("account.move", string="Invoice")
    invoice_line_id = fields.Many2one("account.move.line", string="Invoice Line")
    transform_rule_id = fields.Many2one("product.transform.rule", string="Transform Rule", required=True)
    
    # Products and Quantities
    sold_product_id = fields.Many2one("product.product", string="Sold Product", required=True)
    returned_product_id = fields.Many2one("product.product", string="Returned Product", required=True)
    return_qty = fields.Float(string="Return Quantity", required=True, default=1.0)
    
    pieces_per_sold_unit = fields.Float(string="Pieces per Sold Unit", required=True, default=1.0)
    equivalent_sold_qty = fields.Float(string="Equivalent Sold Quantity", compute="_compute_equivalent_sold_qty", store=True)
    already_returned_qty = fields.Float(string="Already Returned Qty")
    max_return_qty = fields.Float(string="Maximum Return Qty", required=True)
    
    # Target 
    returned_lot_id = fields.Many2one("stock.lot", string="Returned Lot")
    return_to = fields.Selection(related="rma_transform_return_id.return_to")
    customer_location_id = fields.Many2one(related="rma_transform_return_id.customer_location_id")
    
    # Financials
    refund_unit_price = fields.Float(string="Refund Unit Price (Excl. VAT)", compute="_compute_financials", store=True)
    refund_amount = fields.Float(string="Refund Amount (Excl. VAT)", compute="_compute_financials", store=True)
    return_stock_unit_cost = fields.Float(string="Return Stock Unit Cost", compute="_compute_financials", store=True)
    return_stock_value = fields.Float(string="Return Stock Value", compute="_compute_financials", store=True)
    
    rma_reason_id = fields.Many2one("rma.reason", string="RMA Reason")

    @api.depends("return_qty", "pieces_per_sold_unit")
    def _compute_equivalent_sold_qty(self):
        for line in self:
            if line.pieces_per_sold_unit:
                line.equivalent_sold_qty = line.return_qty / line.pieces_per_sold_unit
            else:
                line.equivalent_sold_qty = 0.0

    @api.depends("return_qty", "invoice_line_id", "pieces_per_sold_unit", "original_delivery_line_id")
    def _compute_financials(self):
        for line in self:
            if not line.pieces_per_sold_unit:
                line.refund_unit_price = 0.0
                line.refund_amount = 0.0
                line.return_stock_unit_cost = 0.0
                line.return_stock_value = 0.0
                continue
                
            # Price Calculation from Invoice
            if line.invoice_line_id and line.invoice_line_id.quantity:
                inv_unit_price = line.invoice_line_id.price_subtotal / line.invoice_line_id.quantity
                line.refund_unit_price = inv_unit_price / line.pieces_per_sold_unit
            else:
                line.refund_unit_price = 0.0
                
            line.refund_amount = line.refund_unit_price * line.return_qty
            
            # Cost Calculation from Original Stock Move Layer
            if line.original_delivery_line_id and line.original_delivery_line_id.move_id:
                move = line.original_delivery_line_id.move_id
                svl = move.stock_valuation_layer_ids
                if svl and move.product_uom_qty:
                    total_value = sum(svl.mapped("value"))
                    unit_cost = abs(total_value / move.product_uom_qty)
                    line.return_stock_unit_cost = unit_cost / line.pieces_per_sold_unit
                else:
                    line.return_stock_unit_cost = 0.0
            else:
                line.return_stock_unit_cost = 0.0
                
            line.return_stock_value = line.return_stock_unit_cost * line.return_qty

    @api.constrains("return_qty", "max_return_qty", "equivalent_sold_qty")
    def _check_return_qty(self):
        for line in self:
            if line.return_qty <= 0:
                raise UserError(_("Return quantity must be greater than zero."))
            if float_compare(line.equivalent_sold_qty, line.max_return_qty, precision_rounding=line.sold_product_id.uom_id.rounding) > 0:
                raise UserError(_("Equivalent returned quantity (%(eq_qty)s) cannot exceed the maximum return quantity (%(max_qty)s) for product %(product)s.", 
                                eq_qty=line.equivalent_sold_qty, max_qty=line.max_return_qty, product=line.sold_product_id.display_name))
