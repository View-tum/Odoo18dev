from odoo import models, fields, api


class SaleInvoicePendingPaymentLine(models.TransientModel):
    _name = "sale.invoice.pending.payment.line"
    _description = "Sale Invoice Pending Payment Detail Line"

    wizard_id = fields.Many2one(
        comodel_name="sale.invoice.pending.payment",
        string="Wizard Reference",
        ondelete="cascade",
    )

    invoice_id = fields.Many2one(comodel_name="account.move", string="Invoice")

    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="invoice_id.currency_id",
        string="Currency",
        readonly=True,
    )

    customer_name = fields.Char(
        related="invoice_id.partner_id.name", string="Customer", store=True
    )
    invoice_name = fields.Char(
        related="invoice_id.name", string="Invoice No.", store=True
    )
    datetime_payment_collection = fields.Date(
        related="invoice_id.invoice_date", string="Invoice Date"
    )

    amount_untaxed = fields.Monetary(
        related="invoice_id.amount_untaxed",
        string="Tax Excluded",
        currency_field="currency_id",
    )

    status_in_payment = fields.Selection(
        related="invoice_id.payment_state", string="Status"
    )
    log_timestamp = fields.Datetime(
        string="Payment Collection Date",
        compute="_compute_log_timestamp",
    )

    @api.depends("invoice_id")
    def _compute_log_timestamp(self):
        """
        TH: (Compute) ค้นหาและแสดงวันที่เก็บเงินล่าสุด (Timestamp) จากประวัติการพิมพ์ใบวางบิลของใบแจ้งหนี้นั้นๆ
        EN: (Compute) Retrieves and displays the latest payment collection timestamp from the billing history of the invoice.
        """
        for line in self:
            if not line.invoice_id:
                line.log_timestamp = False
                continue

            last_log = self.env["account.invoice.timestamp"].search(
                [("invoice_ids", "in", line.invoice_id.id)], limit=1
            )

            if last_log:
                line.log_timestamp = last_log.timestamp
            else:
                line.log_timestamp = False
