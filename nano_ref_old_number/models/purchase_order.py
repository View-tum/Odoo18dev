from odoo import api, fields, models, _


class PurchaseOrderInherit(models.Model):
    _inherit = "purchase.order"

    purchase_reason = fields.Text(string='Purchase Reason')
    old_number = fields.Char(string='Old System Number', help="Document number from old system.")


class PurchaseOrderLineInherit(models.Model):
    _inherit = "purchase.order.line"

    old_line_id = fields.Integer(string='Old line ID', help="Order line number from old system.")
