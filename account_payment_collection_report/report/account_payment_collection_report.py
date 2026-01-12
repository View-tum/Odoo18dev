# -*- coding: utf-8 -*-
import datetime
import pytz
from odoo import models, fields, api, Command
from dateutil.relativedelta import relativedelta


class AccountPaymentCollectionReport(models.TransientModel):
    _name = "account.payment.collection.report"
    _description = "Account Payment Collection Report"

    route_id = fields.Many2one(
        comodel_name="delivery.route",
        string="Route",
        help="(365 custom) Select the main route to view data (required when filtering by route).",
    )
    subregion_ids = fields.Many2many(
        comodel_name="delivery.sub.region",
        domain="[('route_id', '=', route_id)]",
        string="Sub-Region",
        help="(365 custom) Specify sub-regions to view data (list shows only regions belonging to the selected route).",
    )
    customer_ids = fields.Many2many(
        comodel_name="res.partner",
        domain="[('is_customer', '=', True)]",
        string="Customers",
        help="(365 custom) Specify customers to include in the report (required when filtering by customer).",
    )

    def _get_year_selection(self):
        """Generate year selection list (Current Year +/- 5)."""
        current_year = fields.Date.today().year
        return [(str(y), str(y)) for y in range(current_year - 5, current_year + 5)]

    select_year = fields.Selection(
        selection=_get_year_selection,
        string="Select Year",
        default=lambda self: str(fields.Date.today().year),
        help="(365 custom) Year for auto-filling the date range.",
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
        help="(365 custom) Month for auto-filling the date range.",
    )
    date_from = fields.Datetime(
        string="Start Date",
        help="(365 custom) Start date and time of the data range (Default is 08:00 AM today).",
    )
    date_to = fields.Datetime(
        string="End Date",
        help="(365 custom) End date and time of the data range (Default is current time).",
    )
    unprinted_only = fields.Boolean(
        string="Unprinted Only",
        default=True,
        help="(365 custom) If selected, the report will show only invoice/payment documents that have not been printed before.",
    )
    report_id = fields.Many2one(
        comodel_name="jasper.report",
        domain=[("model_id", "=", _name)],
        string="Report",
        help="(365 custom) Jasper report template to be used for generating the document (automatically selected by system settings).",
    )

    @api.model
    def default_get(self, fields_list):
        """Initialize default values for dates and report template."""
        res = super(AccountPaymentCollectionReport, self).default_get(fields_list)

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

    @api.onchange("route_id")
    def _onchange_route_id(self):
        """
        When a Route is selected:
            - Automatically selects all associated sub-regions.
            - Initializes default dates and locates the report template.
        """
        self.ensure_one()

        if self.route_id:
            self.subregion_ids = [(6, 0, self.route_id.subregion_ids.ids)]
        else:
            self.subregion_ids = [Command.clear()]

    @api.onchange("select_month", "select_year")
    def _onchange_period(self):
        """Auto-calculate Date From (08:00) and Date To (17:00) based on selected period."""
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
        Confirms report generation: Gathers parameters (route, sub-regions, customers, dates), formats data, and executes the Jasper Report.
        """
        self.ensure_one()

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

        route_id = str(self.route_id.id) if self.route_id else None
        subregion_ids = (
            ",".join(map(str, self.subregion_ids.ids)) if self.subregion_ids else None
        )
        customer_ids = (
            ",".join(map(str, self.customer_ids.ids)) if self.customer_ids else None
        )
        date_from = (
            self.date_from.strftime("%Y-%m-%d %H:%M:%S") if self.date_from else None
        )
        date_to = self.date_to.strftime("%Y-%m-%d %H:%M:%S") if self.date_to else None
        unprinted_only = 1 if self.unprinted_only else None

        data = {
            "route_id": route_id,
            "subregion_ids": subregion_ids,
            "customer_ids": customer_ids,
            "unprinted_only": unprinted_only,
            "date_from": date_from,
            "date_to": date_to,
        }

        return self.report_id.run_report(docids=[self.ids[0]], data=data)
