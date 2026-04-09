from odoo import fields, models, api

class SaleOrderCUS(models.Model):
    _inherit = "sale.order"

    tag_id1 = fields.Many2one('crm.tag', 'Tag1')
    tag_id2 = fields.Many2one('crm.tag', 'Tag2')
    tag_id3 = fields.Many2one('crm.tag', 'Tag3')
    tag_id4 = fields.Many2one('crm.tag', 'Tag4')
    warranty = fields.Many2one('warranty', 'Warranty')
    transports = fields.Many2one('transports', 'Transfer')

    commision = fields.Float(string='Total Commission', compute='_compute_total_commission', store=True)

    @api.depends('order_line.calculate')
    def _compute_total_commission(self):
        for order in self:
            order.commision = sum(line.calculate for line in order.order_line)


class SaleOrderlineCUS(models.Model):
    _inherit = "sale.order.line"

    commision = fields.Float(string='Commission %')
    calculate = fields.Float(string='Commission (unit price)', compute='_compute_calculate', store=True)

    @api.depends('price_subtotal', 'commision')
    def _compute_calculate(self):
        for line in self:
            line.calculate = line.price_subtotal * (line.commision / 100.0)
