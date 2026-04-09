from odoo import fields, models, api


class SaleOrder(models.Model):
    _inherit = "sale.order"

    shipping_gross_weight = fields.Float('Shipping Gross Weight', help="(365 custom)Totoal Shipping Weight")
    number_of_cartons = fields.Integer('Number of Cartons', help="(365 custom)Show total count of cartons")
    toransportation_mode = fields.Selection(
        selection=[
            ('air', 'By Air'),
            ('truck', 'By Truck'),
            ('sea', 'By Sea'),
        ], string='Mode of Transportation',
        tracking=True,
        help="(365 custom)Show transportation type"
    )
    shipping_mark = fields.Text('Shipping Mark', help="(365 custom) User manually type the shipping mark")
    
    @api.onchange('partner_id')
    def _onchange_partner_id_set_shipping_mark(self):
        for order in self:
            if order.partner_id.shipping_mark:
                order.shipping_mark = order.partner_id.shipping_mark
            if order.partner_id.incoterm:
                order.incoterm = order.partner_id.incoterm