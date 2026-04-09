# -*- coding: utf-8 -*-
from odoo import api, fields, exceptions, models, _

class SaleOrder(models.Model):
    _inherit = "sale.order"
    shipping_policy365 = fields.Many2one("sale.order.shipping.policy", string="Export Shipping Policy")
    export_payment_term365 = fields.Many2one("sale.order.export.payment.term", string="Export Payment Term")
    shipping_method = fields.Selection([
        ('self-pickup', 'Self Pick-up'),
        ('shipto-address', 'Ship to Address'),
    ], string='Shipping Method') #
    shipping_address = fields.Text(string="Ship to Address")

    @api.onchange('partner_id')
    def onchange_partner_id_export_payment(self):
        if self.partner_id:
            self.export_payment_term365 = self.partner_id.export_payment_term365

class ResPartner(models.Model):
    _inherit = "res.partner"

    export_payment_term365 = fields.Many2one(
        "sale.order.export.payment.term", 
        string="Export Payment Term",
        help="Default Export Payment Term for this customer."
    )

    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        if self.shipping_method:
            invoice_vals['shipping_method'] = dict(self._fields['shipping_method'].selection).get(self.shipping_method)
        return invoice_vals

class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'
    
    is_show_shipping_method = fields.Boolean(
        string='Show Shipping Method',
        help="(365 custom) If checked, indicates that picking transfers of this type should utilize or display the Shipping Method logic."
    )

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_show_shipping_method = fields.Boolean(
        related='picking_type_id.is_show_shipping_method',
        readonly=True,
    )
    shipping_method = fields.Selection(
        related='sale_id.shipping_method',
        string='Shipping Method',
        readonly=True,
        store=True
    )
    shipping_address = fields.Text(
        related='sale_id.shipping_address',
        string="Ship to Address",
        readonly=True,
        store=True
    )

class SaleOrderShippingPolicy(models.Model):
    _name = "sale.order.shipping.policy"
    _description = "Sale Order Shipping Policy"
    name = fields.Char("Export Shipping Policy")
    shipping_code = fields.Char("Export Shipping Code")

class SaleOrderExportShippingPaymenyTerm(models.Model):
    _name = "sale.order.export.payment.term"
    _description = "Sale Order Export Payment term"
    name = fields.Char("Export Payment Term")
    payment_term_code = fields.Char("Export Payment Term Code")
