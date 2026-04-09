# -*- coding: utf-8 -*-
from odoo import models, fields, api, Command
from odoo.exceptions import UserError


class SaleInvoicePendingPayment(models.TransientModel):
    _name = "sale.invoice.pending.payment"
    _description = "Sale Invoice Pending Payment"

    customer_id = fields.Many2one(
        comodel_name="res.partner",
        domain="[('customer_rank', '>', 0)]",
        string="Customers",
        help="(365 custom) Specify the customer to filter invoices.",
    )

    line_ids = fields.One2many(
        comodel_name="sale.invoice.pending.payment.line",
        inverse_name="wizard_id",
        string="Invoices",
        help="(365 custom) The latest payment collection timestamp retrieved from the billing history.",
    )

    @api.onchange("customer_id")
    def _onchange_customer_id_compute_lines(self):
        """
        TH: (Onchange) ค้นหาใบแจ้งหนี้ที่สถานะ 'Posted' และ 'In Payment' ของลูกค้าที่เลือก แล้วนำมาสร้างเป็นรายการใน Wizard
        EN: (Onchange) Searches for 'Posted' and 'In Payment' invoices for the selected customer and populates them as lines in the wizard.
        """
        self.line_ids = [Command.clear()]

        if not self.customer_id:
            return

        domain = [
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("partner_id", "=", self.customer_id.id),
            ("payment_state", "=", "in_payment"),
        ]

        invoices = self.env["account.move"].search(domain)

        lines_values = []
        for inv in invoices:
            lines_values.append(
                Command.create(
                    {
                        "invoice_id": inv.id,
                    }
                )
            )

        self.line_ids = lines_values
