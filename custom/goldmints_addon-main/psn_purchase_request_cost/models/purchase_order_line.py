from odoo import models, fields, api


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    price_unit = fields.Float(
        string='Unit Price',
        required=False)

    product_qty = fields.Float(
        string='Quantity',
        required=False)

    def onchange_qty_field(self):
        pr_line = self.env['purchase.request.line'].search([('product_id', '=', self.product_id.id)], limit=1)
        self.product_qty = pr_line.product_qty

    @api.onchange('product_id')
    def onchange_qty_id(self):
        pr_line = self.env['purchase.request.line'].search([('product_id', '=', self.product_id.id)], limit=1)
        self.product_qty = pr_line.product_qty

    @api.onchange('product_uom')
    def onchange_price_id(self):
        pr_line = self.env['purchase.request.line'].search([('product_id', '=', self.product_id.id)], limit=1)
        self.price_unit = pr_line.estimated_cost
