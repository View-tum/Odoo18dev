from odoo import models, fields


class DeliveryRouteReportLine(models.TransientModel):
    _name = "delivery.route.report.line"
    _description = "Delivery Route Report Line"
    _order = "subregion_id"

    report_id = fields.Many2one(
        comodel_name="delivery.route.report",
        string="Report Reference",
        ondelete="cascade",
        help="(365 custom) Reference to the parent Delivery Route Report.",
    )
    sale_id = fields.Many2one(
        comodel_name="sale.order",
        string="Sale Order",
        help="(365 custom) ใบสั่งขายที่เกี่ยวข้องกับรายการนี้",
    )
    picking_id = fields.Many2one(
        comodel_name="stock.picking",
        string="Delivery Order",
        help="(365 custom) ใบส่งสินค้าที่เกี่ยวข้องกับรายการนี้",
    )
    subregion_id = fields.Many2one(
        comodel_name="delivery.sub.region",
        related="sale_id.partner_id.subregion_id",
        string="Sub-region",
        readonly=True,
        help="(365 custom) เขตพื้นที่ย่อยที่ลูกค้าของใบสั่งขายนี้อยู่ (ดึงมาจากข้อมูลลูกค้า)",
    )
    ref = fields.Char(
        related="sale_id.partner_id.ref",
        string="Customer Code",
        readonly=True,
        help="(365 custom) รหัสลูกค้าที่เกี่ยวข้องกับใบสั่งขายนี้",
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        related="sale_id.partner_id",
        string="Customer",
        store=True,
        help="(365 custom) ลูกค้าที่เกี่ยวข้องกับใบสั่งขายนี้",
    )
    amount_total = fields.Monetary(
        related="sale_id.amount_total",
        string="Total Amount",
        currency_field="currency_id",
        readonly=True,
        help="(365 custom) จำนวนเงินรวมของใบสั่งขายนี้",
    )
    currency_id = fields.Many2one(
        related="sale_id.currency_id",
        depends=["sale_id"],
        string="Currency",
        readonly=True,
        help="(365 custom) สกุลเงินที่ใช้ในใบสั่งขายนี้",
    )
