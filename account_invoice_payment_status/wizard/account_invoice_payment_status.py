# -*- coding: utf-8 -*-
from odoo import models, fields, api, Command
from dateutil.relativedelta import relativedelta


class AccountInvoicePaymentStatus(models.TransientModel):
    _name = "account.invoice.payment.status"
    _description = "Account Invoice Payment Status"

    name = fields.Char(
        string="Report Name",
        compute="_compute_name",
        help="(365 custom) The display name of the wizard, dynamically generated based on the selected customer.",
    )

    customer_id = fields.Many2one(
        comodel_name="res.partner",
        domain="[('customer_rank', '>', 0)]",
        string="Customer",
        help="(365 custom) Select a specific customer to filter invoices. Leave empty to view all customers.",
    )

    def _get_year_selection(self):
        """
        TH: (Internal) สร้างรายการตัวเลือกปี (ปีปัจจุบัน +/- 5 ปี)
        EN: (Internal) Generates a list of years for selection (Current Year +/- 5).
        """
        current_year = fields.Date.today().year
        return [(str(y), str(y)) for y in range(current_year - 5, current_year + 5)]

    select_year = fields.Selection(
        selection=_get_year_selection,
        string="Select Year",
        default=lambda self: str(fields.Date.today().year),
        help="(365 custom) Select the year to automatically calculate the date range.",
    )
    select_month = fields.Selection(
        [
            ("1", "January"),
            ("2", "February"),
            ("3", "March"),
            ("4", "April"),
            ("5", "May"),
            ("6", "June"),
            ("7", "July"),
            ("8", "August"),
            ("9", "September"),
            ("10", "October"),
            ("11", "November"),
            ("12", "December"),
        ],
        string="Select Month",
        help="(365 custom) Select the month to automatically calculate the date range.",
    )
    date_from = fields.Date(
        string="Start Date",
        help="(365 custom) The starting date for filtering invoices.",
    )
    date_to = fields.Date(
        string="End Date",
        help="(365 custom) The ending date for filtering invoices.",
    )
    line_ids = fields.One2many(
        comodel_name="account.invoice.payment.status.line",
        inverse_name="wizard_id",
        string="Invoices",
        help="(365 custom) The list of invoices retrieved based on the search criteria.",
    )

    @api.model
    def default_get(self, fields_list):
        """
        TH: กำหนดค่าเริ่มต้นให้กับฟิลด์วันที่หากไม่มีการระบุค่ามาเมื่อเปิด Wizard
        EN: Initializes the wizard with default values for date fields if they are not provided.
        """
        res = super(AccountInvoicePaymentStatus, self).default_get(fields_list)

        if "date_to" in fields_list and not res.get("date_to"):
            res["date_to"] = fields.Date.context_today(self)

        if "date_from" in fields_list and not res.get("date_from"):
            res["date_from"] = fields.Date.context_today(self).replace(day=1)

        return res

    @api.onchange("select_month", "select_year")
    def _onchange_period(self):
        """
        TH: (Onchange) คำนวณวันที่เริ่มต้นและสิ้นสุดโดยอัตโนมัติตามเดือนและปีที่ผู้ใช้เลือก
        EN: (Onchange) Automatically calculates the Start Date and End Date based on the selected month and year.
        """
        if self.select_year and self.select_month:
            try:
                year = int(self.select_year)
                month = int(self.select_month)

                first_date = fields.Date.today().replace(year=year, month=month, day=1)
                last_date = first_date + relativedelta(months=1, days=-1)

                self.date_from = first_date
                self.date_to = last_date

            except ValueError:
                pass

    @api.depends("customer_id", "date_from", "date_to")
    def _compute_name(self):
        """
        TH: คำนวณชื่อที่จะแสดงบนหัวข้อ Wizard โดยอิงตามลูกค้าที่เลือก
        EN: Computes the wizard's display name based on the selected customer.
        """
        for record in self:
            if record.customer_id:
                base_name = f"Status: {record.customer_id.name}"
            else:
                base_name = "Invoice Status (All Customers)"

            if record.date_from:
                base_name += f" ({record.date_from} to {record.date_to or '...'})"

            record.name = base_name

    def action_preview(self):
        """
        TH: ค้นหาใบแจ้งหนี้ตามตัวกรอง ดึงวันที่จาก Bank Statement ด้วย SQL และแสดงผลลัพธ์ในตาราง
        EN: Searches for invoices based on filters, retrieves bank statement dates via SQL, and populates the result lines.
        """
        self.ensure_one()

        domain = [
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("invoice_date", ">=", self.date_from),
            ("invoice_date", "<=", self.date_to),
        ]

        if self.customer_id:
            domain.append(("partner_id", "=", self.customer_id.id))

        invoices = self.env["account.move"].search(domain, order="invoice_date desc")

        if not invoices:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "ไม่มีข้อมูลใบแจ้งหนี้",
                    "message": "  • ไม่พบใบแจ้งหนี้ตามเงื่อนไขที่กำหนด",
                    "type": "warning",
                    "sticky": False,
                },
            }

        self.line_ids.unlink()

        # "Dependency on oi_bank_reconciliation table names. Verify if module updated."
        sql_query = """
            WITH invoice_payments AS (
                SELECT
                    invoice.id AS invoice_id,
                    payment.id AS payment_id
                FROM
                    account_move invoice
                JOIN account_move_line aml ON aml.move_id = invoice.id
                JOIN account_partial_reconcile apr ON (apr.debit_move_id = aml.id OR apr.credit_move_id = aml.id)
                JOIN account_move_line counter_aml ON (
                    (counter_aml.id = apr.credit_move_id AND apr.debit_move_id = aml.id)
                    OR
                    (counter_aml.id = apr.debit_move_id AND apr.credit_move_id = aml.id)
                )
                JOIN account_payment payment ON payment.id = counter_aml.payment_id
                WHERE
                    invoice.id IN %(invoice_ids)s
            ),
            statement_dates_from_payment AS (
                SELECT
                    ip.invoice_id,
                    am.date 
                FROM
                    invoice_payments ip
                JOIN bank_statement_line_matched_payment_rel rel ON rel.account_payment_id = ip.payment_id
                JOIN account_bank_statement_line absl ON absl.id = rel.account_bank_statement_line_id
                JOIN account_move am ON am.id = absl.move_id
                WHERE
                    absl.is_reconciled = TRUE
            ),
            statement_dates_direct AS (
                SELECT
                    invoice.id AS invoice_id,
                    am.date
                FROM
                    account_move invoice
                JOIN account_move_line aml ON aml.move_id = invoice.id
                JOIN bank_statement_line_matched_move_line rel ON rel.account_move_line_id = aml.id
                JOIN account_bank_statement_line absl ON absl.id = rel.account_bank_statement_line_id
                JOIN account_move am ON am.id = absl.move_id
                WHERE
                    invoice.id IN %(invoice_ids)s
                    AND absl.is_reconciled = TRUE
            )
            SELECT
                invoice_id,
                MAX(date) as stmt_date
            FROM (
                SELECT * FROM statement_dates_from_payment
                UNION ALL
                SELECT * FROM statement_dates_direct
            ) combined_dates
            GROUP BY invoice_id
        """

        self.env.cr.execute(sql_query, {"invoice_ids": tuple(invoices.ids)})
        result = self.env.cr.fetchall()
        date_map = {r[0]: r[1] for r in result}

        lines_values = []
        for inv in invoices:
            lines_values.append(
                Command.create(
                    {
                        "invoice_id": inv.id,
                        "statement_date": date_map.get(inv.id, False),
                    }
                )
            )

        self.line_ids = lines_values

        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_print_pdf(self):
        """
        TH: ตรวจสอบความถูกต้องของข้อมูลและสั่งพิมพ์รายงาน PDF ผ่าน Jasper Report
        EN: Validates input data and triggers the Jasper Report generation.
        """
        self.ensure_one()

        if self.customer_id is None or not self.line_ids:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "ข้อมูลไม่ครบถ้วน",
                    "message": "  • กรุณาเลือก ลูกค้า ที่มีใบแจ้งหนี้",
                    "type": "danger",
                    "sticky": False,
                },
            }

        report_domain = [("model_id", "=", self._name)]
        found_report = self.env["jasper.report"].search(
            report_domain, order="id", limit=1
        )

        if not found_report:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "การตั้งค่าไม่ถูกต้อง",
                    "message": "  • ไม่พบรายงาน Jasper Report กรุณาตรวจสอบการตั้งค่า",
                    "type": "danger",
                    "sticky": False,
                },
            }

        wizard_id = str(self.id) if self.id else None
        customer_id = str(self.customer_id.id) if self.customer_id else None

        data = {
            "wizard_id": wizard_id,
            "customer_id": customer_id,
        }

        return found_report.run_report(docids=[self.ids[0]], data=data)
