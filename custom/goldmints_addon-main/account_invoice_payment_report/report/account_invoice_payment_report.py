# -*- coding: utf-8 -*-
import datetime
import pytz
from odoo import models, fields, api
from dateutil.relativedelta import relativedelta


class AccountInvoicePaymentReport(models.TransientModel):
    _name = "account.invoice.payment.report"
    _description = "Account Invoice Payment Report"

    team_id = fields.Many2one(
        comodel_name="crm.team",
        string="ทีมขาย",
        help="(365 custom) เลือกทีมขายเพื่อกรองรายชื่อพนักงาน",
    )
    salesperson_ids = fields.Many2many(
        comodel_name="res.users",
        string="พนักงานขาย",
        domain="[('sale_team_id', '=', team_id), ('share', '=', False)] if team_id else []",
        help="(365 custom) ระบุพนักงานขายที่จะรวมในรายงาน",
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
        help="(365 custom) วันที่เริ่มต้นและเวลาของช่วงข้อมูล.",
    )
    date_to = fields.Datetime(
        string="วันที่สิ้นสุด",
        help="(365 custom) วันที่สิ้นสุดและเวลาของช่วงข้อมูล.",
    )
    report_id = fields.Many2one(
        comodel_name="jasper.report",
        domain=[("model_id", "=", _name)],
        string="รายงาน",
        help="(365 custom) เทมเพลตรายงานที่จะใช้ในการสร้างเอกสาร (เลือกโดยระบบตามการตั้งค่า).",
    )

    @api.model
    def default_get(self, fields_list):
        """
        TH: (Override) กำหนดค่าเริ่มต้นสำหรับวันที่ (Date From/To) และเทมเพลตรายงาน
        EN: (Override) Initializes default values for dates (Date From/To) and the report template.
        """
        res = super(AccountInvoicePaymentReport, self).default_get(fields_list)

        if "team_id" in fields_list and not res.get("team_id"):
            team_id = self.env["crm.team"].search([], limit=1, order="id asc")
            res["team_id"] = team_id.id if team_id else False

        if "date_to" in fields_list and not res.get("date_to"):
            res["date_to"] = fields.Datetime.now()

        if "date_from" in fields_list and not res.get("date_from"):
            user_tz = pytz.timezone(self.env.user.tz or "UTC")

            today = fields.Date.context_today(self)
            dt_naive = datetime.datetime.combine(today, datetime.time(8, 0))
            dt_local = user_tz.localize(dt_naive)

            res["date_from"] = dt_local.astimezone(pytz.UTC).replace(tzinfo=None)

        if "report_id" in fields_list and not res.get("report_id"):
            found_report = self.env["jasper.report"].search(
                [("model_id", "=", self._name)], order="id", limit=1
            )
            if found_report:
                res["report_id"] = found_report.id

        return res

    def _get_salesperson_domain(self):
        """
        TH: (Internal) สร้างและส่งคืนค่า Domain (เงื่อนไขการค้นหา) สำหรับฟิลด์ salesperson_ids เพื่อจำกัดให้สามารถเลือกได้เฉพาะผู้ใช้ที่อยู่ในกลุ่ม "Salesman",
            "Salesman All Leads", หรือ "Manager" เท่านั้น
        EN: (Internal) Builds and returns a search domain for the salesperson_ids field, restricting the selectable users to only those who are members of the "Salesman",
            "Salesman All Leads", or "Manager" security groups.
        """
        group_xml_ids = [
            "sales_team.group_sale_salesman",
            "sales_team.group_sale_salesman_all_leads",
            "sales_team.group_sale_manager",
        ]

        sales_group_ids = []
        for xml_id in group_xml_ids:
            group = self.env.ref(xml_id, raise_if_not_found=False)
            if group:
                sales_group_ids.append(group.id)

        domain = [
            ("groups_id", "in", sales_group_ids),
            ("share", "=", False),
            ("company_ids", "in", self.env.company.id),
        ]

        return domain

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

    def action_print_pdf(self):
        """
        TH: (Action) เตรียมข้อมูล ตรวจสอบความถูกต้อง และสั่งพิมพ์รายงาน Jasper Report
        EN: (Action) Prepares data, validates inputs, and executes the Jasper Report generation.
        """
        self.ensure_one()

        if self.date_from and self.date_to and self.date_from > self.date_to:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "วันที่ไม่ถูกต้อง",
                    "message": "  • วันที่เริ่มต้น ต้องมาก่อน หรือวันเดียวกับ วันที่สิ้นสุด",
                    "type": "warning",
                    "sticky": False,
                },
            }

        if not self.report_id:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "การตั้งค่าไม่ถูกต้อง",
                    "message": "  • ไม่พบรายงาน Jasper Report กรุณาตรวจสอบการตั้งค่า",
                    "type": "warning",
                    "sticky": False,
                },
            }

        salesperson_list = self.salesperson_ids.ids
        query = """SELECT am.id FROM account_move am 
                   INNER JOIN account_move__account_payment amap ON amap.invoice_id = am.id
                   INNER JOIN account_payment ap ON ap.id = amap.payment_id 
                   LEFT JOIN res_users ru ON ru.id = am.invoice_user_id
                   WHERE am.payment_state IN ('paid','in_payment') AND am.state = 'posted'
                   AND ap.date >= %s AND ap.date <= %s AND ru.id IN %s LIMIT 1"""

        self.env.cr.execute(
            query, (self.date_from.date(), self.date_to.date(), tuple(salesperson_list))
        )

        if not self.env.cr.fetchone():
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "ไม่พบข้อมูล",
                    "message": "  • ไม่พบข้อมูลในการชำระเงินในช่วงเวลาที่เลือก",
                    "type": "warning",
                    "sticky": False,
                },
            }

        salesperson_ids = (
            ",".join(map(str, self.salesperson_ids.ids))
            if self.salesperson_ids
            else None
        )
        date_from = (
            self.date_from.strftime("%Y-%m-%d %H:%M:%S") if self.date_from else None
        )
        date_to = self.date_to.strftime("%Y-%m-%d %H:%M:%S") if self.date_to else None

        data = {
            "salesperson_ids": salesperson_ids,
            "date_from": date_from,
            "date_to": date_to,
        }
        return self.report_id.run_report(docids=[self.ids[0]], data=data)
