from odoo import fields, models
import odoo


class SaleOrder(models.Model):
    _inherit = "sale.order"

    is_export = fields.Boolean(string="Is Exported?", default=False)
    exported_date = fields.Datetime(string="Exported Date")
    ax_sale_order = fields.Char(string="Sale Number (AX)")

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    is_export = fields.Boolean(string="Is Exported?", default=False)
    exported_date = fields.Datetime(string="Exported Date")


class StagingExportSaleOrder(models.Model):
    _name = "staging.export.sale.order"

    order_id = fields.Integer(string="Order ID")
    exported_date = fields.Datetime(string="Exported Date", default=fields.Datetime.now)


class StagingExportSaleOrderLine(models.Model):
    _name = "staging.export.sale.order.line"

    order_line_id = fields.Integer(string="Order ID")
    exported_date = fields.Datetime(string="Exported Date")


class StagingUpdateAXSaleOrder(models.Model):
    _name = "staging.update.sale.order"

    order_id = fields.Integer(string="Order ID")
    ax_sale_order = fields.Char(string="SO Number (AX)")






