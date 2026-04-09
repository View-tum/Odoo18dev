# -*- coding: utf-8 -*-
import datetime
import pytz
import base64
from odoo import models, fields, api, Command
from dateutil.relativedelta import relativedelta


class AccountPaymentBillingReport(models.TransientModel):
    _name = "account.payment.billing.report"
    _description = "Account Payment Billing Report"

    name = fields.Char(
        string="Report Name",
        compute="_compute_name",
    )
    # --- Filter Section ---
    route_id = fields.Many2one(
        comodel_name="delivery.route",
        string="สาย",
        help="(365 custom) สำหรับเลือกสายการส่งเพื่อกรองข้อมูลในรายงาน",
    )
    subregion_ids = fields.Many2many(
        comodel_name="delivery.sub.region",
        domain="[('route_id', '=', route_id)]",
        string="เขต",
        help="(365 custom) เลือกเขตการส่งเพื่อกรองข้อมูลในรายงาน",
    )
    team_id = fields.Many2one(
        comodel_name="crm.team",
        string="ทีมขาย",
        help="(365 custom) เลือกทีมขายเพื่อกรองรายชื่อพนักงาน",
    )
    salesperson_ids = fields.Many2many(
        comodel_name="res.users",
        string="พนักงานขาย",
        # domain=lambda self: self._get_salesperson_domain(),
        domain="[('sale_team_id', '=', team_id), ('share', '=', False)] if team_id else []",
        help="(365 custom) เลือกพนักงานขายเพื่อกรองข้อมูลในรายงาน ถ้าไม่เลือกจะแสดงข้อมูลของพนักงานขายทั้งหมด",
    )
    customer_ids = fields.Many2many(
        comodel_name="res.partner",
        string="ลูกค้า",
        help="(365 custom) เลือกลูกค้าเพื่อกรองข้อมูลในรายงาน ถ้าไม่เลือกจะแสดงข้อมูลของลูกค้าทั้งหมด",
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
        help="(365 custom) Select year to auto-fill the date range.",
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
        help="(365 custom) Select month to auto-fill the date range.",
    )
    date_from = fields.Datetime(
        string="วันที่เริ่มต้น",
        help="(365 custom) กรองข้อมูลตั้งแต่วันที่และเวลานี้เป็นต้นไป.",
    )
    date_to = fields.Datetime(
        string="วันที่สิ้นสุด",
        help="(365 custom) กรองข้อมูลจนถึงวันที่และเวลานี้.",
    )
    promised_payment_date = fields.Date(
        string="วันที่นัดชำเงิน",
        help="(365 custom) กรองข้อมูลตามวันที่นัดเก็บเงินของใบแจ้งหนี้",
    )
    report_id = fields.Many2one(
        comodel_name="jasper.report",
        domain=[("model_id", "=", _name)],
        string="รายงาน",
        help="(365 custom) เลือกเทมเพลตรายงาน ที่จะใช้สำหรับพิมพ์รายงาน PDF.",
    )
    result_line_ids = fields.One2many(
        comodel_name="account.payment.billing.report.line",
        inverse_name="report_id",
        string="Preview Lines",
        help="(365 custom) Preview lines generated based on the selected filters.",
    )

    @api.model
    def default_get(self, fields_list):
        """
        TH: (Override) กำหนดค่าเริ่มต้นสำหรับวันที่ (Date From/To) และเทมเพลตรายงาน
        EN: (Override) Initializes default values for dates (Date From/To) and the report template.
        """
        res = super(AccountPaymentBillingReport, self).default_get(fields_list)

        # if "date_to" in fields_list and not res.get("date_to"):
        #     res["date_to"] = fields.Datetime.now()

        # if "date_from" in fields_list and not res.get("date_from"):
        #     user_tz = pytz.timezone(self.env.user.tz or "UTC")

        #     today = fields.Date.context_today(self)
        #     dt_naive = datetime.datetime.combine(today, datetime.time(8, 0))
        #     dt_local = user_tz.localize(dt_naive)

        #     res["date_from"] = dt_local.astimezone(pytz.UTC).replace(tzinfo=None)

        if "report_id" in fields_list and not res.get("report_id"):
            found_report = self.env["jasper.report"].search(
                [("model_id", "=", self._name)], order="id", limit=1
            )
            if found_report:
                res["report_id"] = found_report.id

        return res

    # def _get_salesperson_domain(self):
    #     """
    #     TH: (Internal) สร้างและส่งคืนค่า Domain (เงื่อนไขการค้นหา) สำหรับฟิลด์ salesperson_ids เพื่อจำกัดให้สามารถเลือกได้เฉพาะผู้ใช้ที่อยู่ในกลุ่ม "Salesman",
    #         "Salesman All Leads", หรือ "Manager" เท่านั้น
    #     EN: (Internal) Builds and returns a search domain for the salesperson_ids field, restricting the selectable users to only those who are members of the "Salesman",
    #         "Salesman All Leads", or "Manager" security groups.
    #     """
    #     group_xml_ids = [
    #         "sales_team.group_sale_salesman",
    #         "sales_team.group_sale_salesman_all_leads",
    #         "sales_team.group_sale_manager",
    #     ]

    #     sales_group_ids = []
    #     for xml_id in group_xml_ids:
    #         group = self.env.ref(xml_id, raise_if_not_found=False)
    #         if group:
    #             sales_group_ids.append(group.id)

    #     domain = [
    #         ("groups_id", "in", sales_group_ids),
    #         ("share", "=", False),
    #         ("company_ids", "in", self.env.company.id),
    #     ]

    #     return domain

    @api.onchange("route_id")
    def _onchange_route_id(self):
        self.ensure_one()
        self.subregion_ids = [Command.clear()]

    @api.onchange("team_id")
    def _onchange_team_id(self):
        self.ensure_one()
        self.salesperson_ids = [Command.clear()]

    @api.onchange("date_from")
    def _onchange_date_from_time(self):
        if self.date_from:
            user_tz = pytz.timezone(self.env.user.tz or "UTC")
            dt_naive = self.date_from.astimezone(user_tz).replace(
                hour=8, minute=0, second=0
            )
            self.date_from = dt_naive.astimezone(pytz.UTC).replace(tzinfo=None)

    @api.onchange("date_to")
    def _onchange_date_to_time(self):
        if self.date_to:
            now = datetime.datetime.now()
            dt_combined = datetime.datetime.combine(self.date_to.date(), now.time())
            self.date_to = dt_combined

    @api.depends(
        "route_id",
        "subregion_ids",
        "salesperson_ids",
        "date_from",
        "date_to",
        "customer_ids",
    )
    def _compute_name(self):
        for record in self:
            filter_info = "New Report"
            if record.route_id or record.salesperson_ids or record.customer_ids:
                filter_info = "รายงานสรุปเก็บเงิน"

            date_info = ""
            if record.date_from and record.date_to:
                d_from = record.date_from.date().strftime("%d/%m/%Y")
                d_to = record.date_to.date().strftime("%d/%m/%Y")
                date_info = f" ({d_from} - {d_to})"
            elif record.date_from:
                d_from = record.date_from.date().strftime("%d/%m/%Y")
                date_info = f" ({d_from})"

            record.name = f"{filter_info}-{date_info}"

    @api.onchange("select_month", "select_year")
    def _onchange_period(self):
        """
        TH: (Onchange) คำนวณวันที่เริ่มต้น (08:00) และสิ้นสุด (17:00) อัตโนมัติจากเดือนและปีที่เลือก
        EN: (Onchange) Automatically calculates the Start Date (08:00) and End Date (17:00) based on the selected month and year.
        """
        if self.select_year and self.select_month:
            try:
                year = int(self.select_year)
                month = int(self.select_month)

                user_tz_name = self.env.user.tz or "UTC"
                user_tz = pytz.timezone(user_tz_name)

                first_date = fields.Date.today().replace(year=year, month=month, day=1)
                last_date = first_date + relativedelta(months=1, days=-1)

                dt_from_naive = datetime.datetime.combine(
                    first_date, datetime.time(8, 0)
                )
                dt_to_naive = datetime.datetime.combine(last_date, datetime.time(17, 0))

                dt_from_local = user_tz.localize(dt_from_naive)
                dt_to_local = user_tz.localize(dt_to_naive)

                self.date_from = dt_from_local.astimezone(pytz.UTC).replace(tzinfo=None)
                self.date_to = dt_to_local.astimezone(pytz.UTC).replace(tzinfo=None)

            except ValueError:
                pass

    def action_preview(self):
        """
        ดึงข้อมูลตาม SQL Query ที่ระบุและแสดงผลในหน้าจอ (Preview)
        รองรับการกรองด้วย Route และ Sub-Region
        """
        self.ensure_one()

        if not self.promised_payment_date and (not self.date_from or not self.date_to):
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "ขาดข้อมูล",
                    "message": "กรุณาเลือกช่วงวันที่ หรือ วันที่นัดชำระเงิน",
                    "type": "warning",
                },
            }

        if self.date_from and self.date_to and self.date_from > self.date_to:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "วันที่ไม่ถูกต้อง",
                    "message": "  • วันที่เริ่มต้น ต้องมาก่อน หรือวันเดียวกับ วันที่สิ้นสุด",
                    "type": "danger",
                    "sticky": False,
                },
            }
            
        where_conditions = """
            am.move_type = 'out_invoice'
            AND am.state = 'posted'
            AND am.amount_total > 0
            AND (aitamr.account_move_id IS NOT NULL OR ab.id IS NOT NULL)
        """
        params = []

        if self.promised_payment_date:
            where_conditions += " AND abl.promised_payment_date = %s"
            params.append(self.promised_payment_date)
        else:
            where_conditions += (
                " AND am.invoice_date >= DATE(%s) AND am.invoice_date <= DATE(%s)"
            )
            params.extend([self.date_from, self.date_to])

        if self.salesperson_ids:
            where_conditions += " AND am.invoice_user_id IN %s"
            if len(self.salesperson_ids) == 1:
                params.append((self.salesperson_ids.id,))
            else:
                params.append(tuple(self.salesperson_ids.ids))
        elif self.subregion_ids:
            where_conditions += " AND rp.subregion_id IN %s"
            if len(self.subregion_ids) == 1:
                params.append((self.subregion_ids.id,))
            else:
                params.append(tuple(self.subregion_ids.ids))
        elif self.route_id:
            where_conditions += " AND sub.route_id = %s"
            params.append(self.route_id.id)
        elif self.customer_ids:
            where_conditions += " AND am.partner_id IN %s"
            params.append(tuple(self.customer_ids.ids))

        query = f"""
            SELECT 
                am.id as move_id,
                am.name as invoice_name,
                am.invoice_date,
                am.invoice_date_due as due_date,
                am.currency_id,
                am.amount_total,
                rpu.name as sale_name,
                dr.name as route_name,
                sub.name as subregion_name,
                rp.ref as partner_code,
                rp.name as partner_name,
                COALESCE(rp.account_note, '') as account_note,
                CASE 
                    WHEN COUNT(aitamr.account_move_id) > 0 AND COUNT(ab.id) > 0 THEN 'ฝากเก็บ, ฝากวางบิล'
                    WHEN COUNT(aitamr.account_move_id) > 0 THEN 'ฝากเก็บ'
                    WHEN COUNT(ab.id) > 0 THEN 'ฝากวางบิล'
                    ELSE ''
                END as invoice_summary
            FROM account_move am
            LEFT JOIN res_company rc ON rc.id = am.company_id
            LEFT JOIN account_invoice_timestamp_account_move_rel aitamr ON aitamr.account_move_id = am.id
            LEFT JOIN account_billing_line abl ON abl.move_id = am.id AND abl.billing_id IS NOT NULL
            LEFT JOIN account_billing ab ON ab.id = abl.billing_id AND ab.state = 'billed'
            INNER JOIN res_partner rp ON rp.id = am.partner_id
            LEFT JOIN delivery_sub_region sub ON sub.id = rp.subregion_id
            LEFT JOIN delivery_route dr ON dr.id = sub.route_id
            LEFT JOIN res_users ru ON ru.id = am.invoice_user_id
            INNER JOIN res_partner rpu ON rpu.id = ru.partner_id
            
            WHERE {where_conditions}
            
            GROUP BY 
                am.id,
                am.name,
                am.invoice_date,
                am.currency_id,
                am.amount_total, 
                dr.name,
                sub.name,
                rp.ref,
                rp.name,
                rp.account_note,
                rp.id,
                rpu.name,
                rpu.id
                
            ORDER BY 
                dr.name,
                sub.name,
                rp.ref,
                am.name
        """

        self.env.cr.execute(query, tuple(params))
        results = self.env.cr.dictfetchall()
        self.result_line_ids.unlink()

        lines = []
        for index, res in enumerate(results, start=1):
            lines.append(
                Command.create(
                    {
                        "move_id": res.get("move_id"),
                        "route_name": res.get("route_name"),
                        "subregion_name": res.get("subregion_name"),
                        "partner_code": res.get("partner_code"),
                        "partner_name": res.get("partner_name"),
                        "account_note": res.get("account_note") or "",
                        "invoice_name": res.get("invoice_name"),
                        "currency_id": res.get("currency_id"),
                        "amount_total": res.get("amount_total"),
                        "invoice_summary": res.get("invoice_summary"),
                        "invoice_date": res.get("invoice_date"),
                        "due_date": res.get("due_date"),
                        "sale_name": res.get("sale_name"),
                        # "sequence": index,
                    }
                )
            )

        self.write({"result_line_ids": lines})

        return {
            "type": "ir.actions.act_window",
            "res_model": "account.payment.billing.report",
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_print_excel(self):
        """
        สร้างไฟล์ Excel โดยเรียกใช้ Logic จากไฟล์ account_payment_billing_report_excel.py
        """
        self.ensure_one()

        if not self.result_line_ids:
            self.action_preview()

        if not self.result_line_ids:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "ไม่พบข้อมูล",
                    "message": "กรุณากด Preview หรือตรวจสอบเงื่อนไขการค้นหา",
                    "type": "warning",
                    "sticky": False,
                },
            }

        report_xlsx = self.env["report.account_payment_billing_excel"].new()
        file_content = report_xlsx.generate_xlsx_report(self)
        file_name = f"Payment_Billing_{fields.Date.today()}.xlsx"
        attachment = self.env["ir.attachment"].create(
            {
                "name": file_name,
                "type": "binary",
                "datas": base64.b64encode(file_content),
                "res_model": self._name,
                "res_id": self.id,
                "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            }
        )

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "self",
        }

    def action_print_pdf(self):
        """
        TH: (Action) เตรียมข้อมูล ตรวจสอบความถูกต้อง และสั่งพิมพ์รายงาน Jasper Report
        EN: (Action) Prepares data, validates inputs, and executes the Jasper Report generation.
        """
        self.ensure_one()

        if not self.report_id:
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

        data = {
            "wizard_id": self.id,
        }
        return self.report_id.run_report(docids=[self.ids[0]], data=data)
