from odoo import models, fields, api


class SaleCommissionTimestamp(models.Model):
    _name = "sale.commission.timestamp"
    _description = "Sale Commission Timestamp Log"
    _order = "create_date desc"

    salesperson_id = fields.Many2one(
        comodel_name="res.users", string="Salesperson", required=True, readonly=True
    )
    sale_order_name = fields.Char(string="Sale Order", readonly=True)
    invoice_names = fields.Char(string="Invoices", readonly=True)
    commission_amount = fields.Float(string="Commission Amount", readonly=True)
    log_date = fields.Datetime(
        string="Log Date", default=fields.Datetime.now, readonly=True
    )
