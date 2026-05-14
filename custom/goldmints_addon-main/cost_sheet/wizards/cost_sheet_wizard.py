# wizards/cost_sheet_wizard.py
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, date
import io
import base64
import xlsxwriter


class CostSheetWizard(models.TransientModel):
    _name = "cost.sheet.wizard"
    _description = "Cost Sheet Wizard"

    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        string="Company",
    )

    period_id = fields.Many2one(
        "ff.month.period",
        string="Period",
        domain=lambda self: [
            ("date_from", ">=", date(fields.Date.context_today(self).year, 1, 1)),
            ("date_from", "<",  date(fields.Date.context_today(self).year + 1, 1, 1)),
        ],
    )

    date_from    = fields.Date(required=True, string="Date From")
    date_to      = fields.Date(required=True, string="Date To")
    description  = fields.Char(string="Description")
    show_details = fields.Boolean(default=True, string="Show Details")

    # ------------------------------------------------------------------
    #  Default get — สร้าง period ปีปัจจุบันถ้ายังไม่มี
    # ------------------------------------------------------------------

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        self.env["ff.month.period"].sudo().ensure_current_year_periods()
        return res

    # ------------------------------------------------------------------
    #  Onchange
    # ------------------------------------------------------------------

    @api.onchange("period_id")
    def _onchange_period_id(self):
        """เลือก Period -> เติม date_from / date_to อัตโนมัติ"""
        if self.period_id:
            self.date_from = self.period_id.date_from
            self.date_to   = self.period_id.date_to

    @api.onchange("date_from", "date_to")
    def _onchange_dates_clear_period(self):
        """แก้วันที่เองไม่ตรง period -> ล้าง period_id"""
        if not self.period_id:
            return
        if (self.date_from != self.period_id.date_from
                or self.date_to != self.period_id.date_to):
            self.period_id = False

    # ------------------------------------------------------------------
    #  Validations / helpers
    # ------------------------------------------------------------------

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for wizard in self:
            if wizard.date_from and wizard.date_to and wizard.date_from > wizard.date_to:
                raise ValidationError(_("Start Date must be before End Date."))

    def _get_landed_costs(self):
        self.ensure_one()
        domain = [
            ("company_id", "=", self.company_id.id),
            ("state",      "=", "done"),
        ]
        if self.date_from:
            domain.append(("date", ">=", self.date_from))
        if self.date_to:
            domain.append(("date", "<=", self.date_to))
        return self.env["stock.landed.cost"].search(domain, order="date, name")

    def _get_report_base_filename(self):
        self.ensure_one()
        df = self.date_from.strftime("%Y-%m-%d") if self.date_from else ""
        dt = self.date_to.strftime("%Y-%m-%d")   if self.date_to   else ""
        return f"Cost Sheet - {df} to {dt}"

    # ------------------------------------------------------------------
    #  Report actions
    # ------------------------------------------------------------------

    def _report_action(self, report_xmlid, report_type="qweb-pdf"):
        self.ensure_one()
        action = self.env.ref(report_xmlid).report_action(
            self, data={"wizard_id": self.id}
        )
        action["report_type"] = report_type
        return action

    def action_view_html(self):
        return self._report_action("cost_sheet.action_report_cost_sheet", "qweb-html")

    def action_export_pdf(self):
        return self._report_action("cost_sheet.action_report_cost_sheet", "qweb-pdf")

    def action_export_xlsx(self):
        self.ensure_one()

        bio = io.BytesIO()
        workbook = xlsxwriter.Workbook(bio, {"in_memory": True})

        report_model = self.env["report.cost_sheet.report_cost_sheet_xlsx"]
        report_model.generate_xlsx_report(workbook, {}, self)

        workbook.close()
        xlsx_data = bio.getvalue()
        bio.close()

        filename = "cost_sheet_%s.xlsx" % datetime.now().strftime("%Y%m%d_%H%M%S")

        att = self.env["ir.attachment"].create({
            "name":      filename,
            "type":      "binary",
            "datas":     base64.b64encode(xlsx_data),
            "res_model": self._name,
            "res_id":    self.id,
            "mimetype":  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "public":    False,
        })

        return {
            "type":   "ir.actions.act_url",
            "url":    "/web/content/%s?download=true" % att.id,
            "target": "self",
        }