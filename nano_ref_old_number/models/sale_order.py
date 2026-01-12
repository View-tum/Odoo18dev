from odoo import api, fields, models, _


class SaleOrderInherit(models.Model):
    _inherit = "sale.order"

    old_number = fields.Char(string='Old System Number', help="Document number from old system.")
    delivery_remark = fields.Text(string='Delivery Remark')
    notes = fields.Text(string='Notes')



class SaleOrderLineInherit(models.Model):
    _inherit = "sale.order.line"

    old_line_id = fields.Integer(string='Old line ID', help="Order line number from old system.")
