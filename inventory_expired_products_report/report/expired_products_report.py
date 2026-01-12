# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from datetime import datetime


class ExpiredProductsReport(models.TransientModel):
    _name = "expired.products.report"
    _description = "Expired Products Report"

    # ==============================================================================================
    #                                          FILTERS
    # ==============================================================================================
    product_category_id = fields.Many2one(
        comodel_name="product.category",
        string="Product Category",
        help="(365 custom) Select product category to filter products in report.",
    )

    product_ids = fields.Many2many(
        comodel_name="product.product",
        string="Product",
        help="(365 custom) Select product to filter in report.",
    )

    # ==============================================================================================
    #                                     DATE SELECTION
    # ==============================================================================================
    def _get_year_selection(self):
        """
        Generate a list of years for selection.
        Range: Current year - 5 years to Current year + 5 years.
        Returns: List of tuples [(str, str)]
        """
        current_year = int(fields.Date.context_today(self).year)
        return [(str(y), str(y)) for y in range(current_year - 5, current_year + 6)]

    select_year = fields.Selection(
        selection=_get_year_selection,
        string="Select Year",
        help="Select year for the report range.",
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
        help="Select a month to auto-fill Date From and Date To.",
    )

    date_from = fields.Date(
        string="Date From",
        help="(365 custom) The start date for the report's data range.",
    )
    date_to = fields.Date(
        string="Date To",
        help="(365 custom) The end date for the report's data range.",
    )

    # ==============================================================================================
    #                                     REPORT CONFIG
    # ==============================================================================================
    report_id = fields.Many2one(
        comodel_name="jasper.report",
        string="Report",
        required=True,
        domain=[("model_id", "=", "expired.products.report")],
        help="(365 custom) Select the Jasper Report template to be used for this summary.",
    )

    @api.model
    def default_get(self, fields_list):
        """
        Set default values for the wizard.
        - Auto-select the Jasper Report template if available.
        """
        res = super(ExpiredProductsReport, self).default_get(fields_list)

        # Default report if not set
        if "report_id" not in res:
            report = self.env["jasper.report"].search(
                [("model_id", "=", self._name)], limit=1
            )
            if report:
                res["report_id"] = report.id

        return res

    # ==============================================================================================
    #                                     ONCHANGE METHODS
    # ==============================================================================================
    @api.onchange("select_month", "select_year")
    def _onchange_month_year(self):
        """
        Calculates and sets 'date_from' and 'date_to' based on the selected month and year.
        - If Month is selected but Year is empty -> Defaults Year to current year.
        - Calculates the first and last day of the selected month.
        """
        if self.select_month:
            year_val = self.select_year
            if not year_val:
                year_val = str(fields.Date.context_today(self).year)
                self.select_year = year_val

            try:
                month = int(self.select_month)
                year = int(year_val)

                start_date = fields.Date.context_today(self).replace(
                    year=year, month=month, day=1
                )
                end_date = start_date + relativedelta(day=31)

                self.date_from = start_date
                self.date_to = end_date
            except ValueError:
                pass

    @api.onchange("select_month")
    def _onchange_month(self):
        """
        Clears 'date_from' and 'date_to' if 'select_month' is cleared by the user.
        """
        if not self.select_month:
            self.date_from = False
            self.date_to = False

    @api.onchange("date_from", "date_to")
    def _onchange_dates(self):
        """
        Updates configuration based on manual date changes.
        - Syncs 'select_year' to match the year of 'date_from'.
        - Does NOT modify 'select_month' (allows custom date ranges without clearing the month filter).
        """
        if self.date_from:
            # Sync year based on custom date
            self.select_year = str(self.date_from.year)

    @api.onchange("product_category_id")
    def _onchange_product_category_id(self):
        """Ensure mutual exclusivity: Clear Products if Category is selected."""
        if self.product_category_id:
            self.product_ids = [(5, 0, 0)]  # Clear Many2many

    @api.onchange("product_ids")
    def _onchange_product_ids(self):
        """Ensure mutual exclusivity: Clear Category if Products are selected."""
        if self.product_ids:
            self.product_category_id = False  # Clear Many2one

    # ==============================================================================================
    #                                     CONSTRAINTS & ACTIONS
    # ==============================================================================================
    @api.constrains("date_from", "date_to")
    def _check_date_range_constrains(self):
        """
        Validates the date range.
        - Ensures date_from <= date_to.
        - Ensures both dates are present if one is set (though XML might handle required).
        """
        for record in self:
            if record.date_from and record.date_to:
                if record.date_from > record.date_to:
                    raise UserError(
                        "วันที่เริ่มต้น (Date From) ต้องมาก่อน หรือวันเดียวกับ วันที่สิ้นสุด (Date To)"
                    )

            # Check mandatory pairs
            if (record.date_to and not record.date_from) or (
                record.date_from and not record.date_to
            ):
                raise UserError("กรุณากรอกช่วงวันที่ให้ครบถ้วน (Date From และ Date To)")

    def action_confirm(self):
        """
        Executes the report generation.
        - Prepares data dictionary for Jasper Report parameters.
        - Converts Odoo objects/dates to simple types (str) for the report engine.
        """
        self.ensure_one()

        if not self.report_id:
            raise UserError("ไม่พบรายงาน Jasper ที่กำหนดไว้")

        product_category_id = (
            str(self.product_category_id.id) if self.product_category_id else None
        )

        product_ids = (
            ",".join(map(str, self.product_ids.ids)) if self.product_ids else None
        )

        year = str(self.select_year) if self.select_year else None
        month = str(self.select_month) if self.select_month else None

        date_from = self.date_from.strftime("%Y-%m-%d") if self.date_from else None
        date_to = self.date_to.strftime("%Y-%m-%d") if self.date_to else None

        data = {
            "product_category_id": product_category_id,
            "product_ids": product_ids,
            "year": year,
            "month": month,
            "date_from": date_from,
            "date_to": date_to,
        }

        return self.report_id.run_report(docids=[self.id], data=data)
