# -*- coding: utf-8 -*-
from odoo import models, fields, api, Command
from dateutil.relativedelta import relativedelta


class AccountInvoicePaymentStatus(models.TransientModel):
    _name = "account.invoice.payment.status"
    _description = "Account Invoice Payment Status"

    name = fields.Char(
        string="Report Name",
        compute="_compute_name",
    )

    # --- Filter Section ---
    route_id = fields.Many2one(
        comodel_name="delivery.route",
        string="สาย",
        help="(365 custom) เลือกสายการส่งเพื่อกรองลูกค้าในเขตที่เกี่ยวข้อง",
    )
    subregion_ids = fields.Many2many(
        comodel_name="delivery.sub.region",
        domain="[('route_id', '=', route_id)]",
        string="เขต",
        help="(365 custom) เลือกเขตการส่งเพื่อกรองลูกค้าในเขตที่เกี่ยวข้อง",
    )
    customer_ids = fields.Many2many(
        comodel_name="res.partner",
        domain="[('customer_rank', '>', 0)]",
        string="ลูกค้า",
        help="(365 custom) เลือกลูกค้าเพื่อกรองข้อมูลใบแจ้งหนี้",
    )
    team_id = fields.Many2one(
        comodel_name="crm.team",
        string="ทีมขาย",
        help="(365 custom) เลือกทีมขายเพื่อกรองรายชื่อพนักงาน",
    )
    salesperson_ids = fields.Many2many(
        comodel_name="res.users",
        string="พนักงานขาย",
        domain="[('sale_team_id', '=', team_id), ('share', '=', False)] if team_id else []",
        help="(365 custom) ระบุพนักงานขายที่จะหาในรายงาน",
    )
    payment_state = fields.Selection(
        selection=[
            ("not_paid", "ยังไม่ชำระ"),
            ("in_payment", "อยู่ระหว่างการชำระ"),
            ("paid", "ชำระแล้ว"),
            ("partial", "ชำระบางส่วน"),
            ("reversed", "ย้อนกลับ"),
        ],
        string="สถานะการชำระเงิน",
        help="(365 custom) กรองใบแจ้งหนี้ตามสถานะการชำระเงินที่เลือก",
    )

    # --- Date Section ---
    def _get_year_selection(self):
        current_year = fields.Date.today().year
        return [(str(y), str(y)) for y in range(current_year - 5, current_year + 5)]

    select_year = fields.Selection(
        selection=_get_year_selection,
        string="Select Year",
        default=lambda self: str(fields.Date.today().year),
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
    )
    date_from = fields.Date(
        string="วันที่เริ่มต้น", help="(365 custom) กรองใบแจ้งหนี้ตั้งแต่วันที่นี้เป็นต้นไป (Invoice Date)"
    )
    date_to = fields.Date(
        string="วันที่สิ้นสุด", help="(365 custom) กรองใบแจ้งหนี้จนถึงวันที่นี้ (Invoice Date)"
    )

    # --- Result Lines ---
    invoice_line_ids = fields.One2many(
        comodel_name="account.invoice.payment.status.line",
        inverse_name="wizard_id",
        string="Invoices Found",
    )

    @api.model
    def default_get(self, fields_list):
        res = super(AccountInvoicePaymentStatus, self).default_get(fields_list)
        if "date_to" in fields_list and not res.get("date_to"):
            res["date_to"] = fields.Date.context_today(self)
        if "date_from" in fields_list and not res.get("date_from"):
            res["date_from"] = fields.Date.context_today(self).replace(day=1)
        return res

    @api.onchange("route_id")
    def _onchange_route_id(self):
        self.ensure_one()
        self.subregion_ids = [Command.clear()]

    @api.onchange("team_id")
    def _onchange_team_id(self):
        self.ensure_one()
        self.salesperson_ids = [Command.clear()]

    @api.onchange("select_month", "select_year")
    def _onchange_period(self):
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

    @api.depends("date_from", "date_to")
    def _compute_name(self):
        for record in self:
            if record.date_from and record.date_to:
                d_from = record.date_from.strftime("%d/%m/%Y")
                d_to = record.date_to.strftime("%d/%m/%Y")
                record.name = f"ตรวจสอบสถานะใบแจ้งหนี้ ({d_from} - {d_to})"

    def action_preview(self):
        self.ensure_one()

        domain = [
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("invoice_date", ">=", self.date_from),
            ("invoice_date", "<=", self.date_to),
        ]

        target_partner_ids = []
        if self.customer_ids:
            target_partner_ids = self.customer_ids.ids
            domain.append(("partner_id", "in", target_partner_ids))
        elif self.subregion_ids:
            customers_in_region = self.env["res.partner"].search(
                [("subregion_id", "in", self.subregion_ids.ids)]
            )
            target_partner_ids = customers_in_region.ids
            if not target_partner_ids:
                return self._show_warning("ไม่พบลูกค้า", "ไม่พบลูกค้าในพื้นที่การส่งที่เลือก")
            domain.append(("partner_id", "in", target_partner_ids))
        elif self.salesperson_ids:
            domain.append(("invoice_user_id", "in", self.salesperson_ids.ids))

        if self.payment_state:
            domain.append(("payment_state", "=", self.payment_state))
        else:
            domain.append(
                ("payment_state", "in", ["not_paid", "in_payment", "partial", "paid"])
            )

        invoices = self.env["account.move"].search(
            domain, order="invoice_date desc, name desc"
        )

        if not invoices:
            return self._show_warning("ไม่พบข้อมูลใบแจ้งหนี้", "ไม่พบใบแจ้งหนี้ตามเงื่อนไขที่กำหนด")

        self.invoice_line_ids.unlink()
        # date_map = self._get_statement_dates(invoices)

        invoice_vals_list = []

        for inv in invoices:
            invoice_vals_list.append(
                {
                    "wizard_id": self.id,
                    "invoice_id": inv.id,
                    # "statement_date": date_map.get(inv.id, False),
                }
            )

        self.env["account.invoice.payment.status.line"].create(invoice_vals_list)
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    # def _get_statement_dates(self, invoices):
    #     """Helper to fetch statement dates using SQL"""
    #     sql_query = """
    #         WITH invoice_payments AS (
    #             SELECT invoice.id AS invoice_id, payment.id AS payment_id
    #             FROM account_move invoice
    #             JOIN account_move_line aml ON aml.move_id = invoice.id
    #             JOIN account_partial_reconcile apr ON (apr.debit_move_id = aml.id OR apr.credit_move_id = aml.id)
    #             JOIN account_move_line counter_aml ON (
    #                 (counter_aml.id = apr.credit_move_id AND apr.debit_move_id = aml.id) OR
    #                 (counter_aml.id = apr.debit_move_id AND apr.credit_move_id = aml.id)
    #             )
    #             JOIN account_payment payment ON payment.id = counter_aml.payment_id
    #             WHERE invoice.id IN %(invoice_ids)s
    #         ),
    #         statement_dates_from_payment AS (
    #             SELECT ip.invoice_id, am.date
    #             FROM invoice_payments ip
    #             JOIN bank_statement_line_matched_payment_rel rel ON rel.account_payment_id = ip.payment_id
    #             JOIN account_bank_statement_line absl ON absl.id = rel.account_bank_statement_line_id
    #             JOIN account_move am ON am.id = absl.move_id
    #             WHERE absl.is_reconciled = TRUE
    #         ),
    #         statement_dates_direct AS (
    #             SELECT invoice.id AS invoice_id, am.date
    #             FROM account_move invoice
    #             JOIN account_move_line aml ON aml.move_id = invoice.id
    #             JOIN bank_statement_line_matched_move_line rel ON rel.account_move_line_id = aml.id
    #             JOIN account_bank_statement_line absl ON absl.id = rel.account_bank_statement_line_id
    #             JOIN account_move am ON am.id = absl.move_id
    #             WHERE invoice.id IN %(invoice_ids)s AND absl.is_reconciled = TRUE
    #         )
    #         SELECT invoice_id, MAX(date) as stmt_date
    #         FROM (
    #             SELECT * FROM statement_dates_from_payment
    #             UNION ALL
    #             SELECT * FROM statement_dates_direct
    #         ) combined_dates
    #         GROUP BY invoice_id
    #     """
    #     self.env.cr.execute(sql_query, {"invoice_ids": tuple(invoices.ids)})
    #     result = self.env.cr.fetchall()
    #     return {r[0]: r[1] for r in result}

    def _show_warning(self, title, message):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": message,
                "type": "warning",
                "sticky": False,
            },
        }

    def action_print_pdf(self):
        self.ensure_one()
        if not self.invoice_line_ids:
            return self._show_warning("ไม่มีข้อมูล", "กรุณากด Preview เพื่อดึงข้อมูลก่อนพิมพ์")

        report_domain = [("model_id", "=", self._name)]
        found_report = self.env["jasper.report"].search(
            report_domain, order="id", limit=1
        )

        if not found_report:
            return self._show_warning("ไม่พบรายงาน", "ไม่พบรายงานที่เพื่อใช้ในการพิมพ์")

        data = {
            "wizard_id": str(self.id),
        }
        return found_report.run_report(docids=[self.id], data=data)
