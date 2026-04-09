# Copyright 2019 Ecosoft Co., Ltd (https://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

import re

from odoo import api, fields, models

INCOME_TAX_FORM = {
    "pnd1": "P01",
    "pnd1a": "P01A",
    "pnd2": "P02",
    "pnd3": "P03",
    "pnd53": "P53",
}


class WithHoldingTaxReportWizard(models.TransientModel):
    _name = "withholding.tax.report.wizard"
    _inherit = "account.tax.report.abstract.wizard"
    _description = "Withholding Tax Report Wizard"

    income_tax_form = fields.Selection(
        selection=[
            ("pnd1", "PND1"),
            ("pnd1a", "PND1A"),
            ("pnd2", "PND2"),
            ("pnd3", "PND3"),
            ("pnd53", "PND53"),
        ],
        required=True,
    )
    company_wht_report_format = fields.Selection(
        related="company_id.wht_report_format",
    )
    rd_sender_id = fields.Char(
        string="RD Sender ID",
        default="0000",
        help="Revenue Department sender ID. Use 0000 for media/file upload.",
    )
    rd_sender_nid = fields.Char(
        string="RD Sender Tax ID",
        default=lambda self: self._default_rd_sender_nid(),
        help="13-digit Tax ID of the sender.",
    )
    rd_sender_branch = fields.Char(
        string="RD Sender Branch",
        default=lambda self: self._default_rd_sender_branch(),
        help="Branch of sender in 6 digits. Head office is 000000.",
    )
    rd_sender_role = fields.Selection(
        selection=[
            ("1", "1 - Withholding Agent"),
            ("2", "2 - Agent"),
            ("3", "3 - Intermediary"),
            ("4", "4 - Combined Filing"),
        ],
        string="RD Sender Role",
        default="1",
    )
    rd_dept_name = fields.Char(
        string="RD Department / Branch Name",
        default="สำนักงานใหญ่",
    )
    rd_lto = fields.Boolean(
        string="LTO",
        default=False,
    )
    rd_branch_type = fields.Selection(
        selection=[
            ("", "Blank"),
            ("V", "VAT Branch"),
            ("S", "SBT Branch"),
        ],
        string="RD Branch Type",
        default="V",
    )
    rd_form_type = fields.Char(
        string="RD Form Type",
        default="00",
        help="00 = regular filing, 01-99 = additional filing.",
    )
    rd_submission_seq = fields.Char(
        string="RD Submission Sequence",
        default="00",
        help="00-99, used in official filename.",
    )
    rd_form_flag = fields.Selection(
        selection=[
            ("1", "1 - File Upload"),
            ("2", "2 - Internet Filing"),
        ],
        string="RD Form Flag",
        default="1",
    )
    rd_user_id = fields.Char(
        string="RD User ID / Registration ID",
        help="Revenue Department filing user ID or media registration ID.",
    )
    rd_sur_amt = fields.Float(
        string="RD Surcharge Amount",
        digits=(16, 2),
        default=0.0,
    )
    rd_trans_amt = fields.Float(
        string="RD Transfer Amount",
        digits=(16, 2),
        default=0.0,
    )
    rd_section3 = fields.Boolean(string="Section 3", default=False)
    rd_section48 = fields.Boolean(string="Section 48", default=False)
    rd_section50 = fields.Boolean(string="Section 50", default=False)
    rd_section65 = fields.Boolean(string="Section 65", default=False)
    rd_section69 = fields.Boolean(string="Section 69", default=False)

    @api.model
    def _default_rd_sender_nid(self):
        return re.sub(r"\D", "", self.env.company.partner_id.vat or "")

    @api.model
    def _default_rd_sender_branch(self):
        partner = self.env.company.partner_id
        branch = getattr(partner, "branch", False) or partner.company_registry or ""
        return re.sub(r"\D", "", branch)

    def _get_report_base_filename(self):
        self.ensure_one()
        if (
            self.company_id.wht_report_format == "rd"
            and self.income_tax_form in ("pnd3", "pnd53")
        ):
            company_partner = self.company_id.partner_id
            company_tax_id = re.sub(r"\D", "", company_partner.vat or "")
            branch = (
                getattr(company_partner, "branch", False)
                or company_partner.company_registry
                or ""
            )
            branch = re.sub(r"\D", "", branch).zfill(6)[-6:] if branch else "000000"
            tax_year = str(self.date_from.year + 543)
            tax_month = f"{self.date_from.month:02d}"
            tax_type = self.income_tax_form.upper()
            form_type = (self.rd_form_type or "00").zfill(2)[-2:]
            submission_seq = (self.rd_submission_seq or "00").zfill(2)[-2:]
            return (
                f"{tax_type}_{company_tax_id}_{branch}_{tax_year}_"
                f"{tax_month}_{form_type}_{submission_seq}"
            )
        pnd = INCOME_TAX_FORM[self.income_tax_form]
        date_format = self.format_thai_date(
            self.date_from, month_format="numeric", format_date="{year}{month}"
        )
        return f"WHT-{pnd}-{date_format}"

    def _prepare_report_wht(self):
        self.ensure_one()
        return {
            "wizard_id": self.id,
            "company_id": self.company_id.id,
            "date_from": self.date_from,
            "date_to": self.date_to,
            "income_tax_form": self.income_tax_form,
            "show_cancel": self.show_cancel,
            "rd_sender_id": self.rd_sender_id,
            "rd_sender_nid": self.rd_sender_nid,
            "rd_sender_branch": self.rd_sender_branch,
            "rd_sender_role": self.rd_sender_role,
            "rd_dept_name": self.rd_dept_name,
            "rd_lto": self.rd_lto,
            "rd_branch_type": self.rd_branch_type,
            "rd_form_type": self.rd_form_type,
            "rd_submission_seq": self.rd_submission_seq,
            "rd_form_flag": self.rd_form_flag,
            "rd_user_id": self.rd_user_id,
            "rd_sur_amt": self.rd_sur_amt,
            "rd_trans_amt": self.rd_trans_amt,
            "rd_section3": self.rd_section3,
            "rd_section48": self.rd_section48,
            "rd_section50": self.rd_section50,
            "rd_section65": self.rd_section65,
            "rd_section69": self.rd_section69,
        }

    def button_export_txt(self):
        self.ensure_one()
        report_type = "qweb-text"
        return self._export(report_type)

    def _get_report_name(self, report_type):
        self.ensure_one()
        data = self._prepare_report_wht()
        if report_type == "xlsx":
            report_name = "l10n_th_account_tax_report.report_withholding_tax_xlsx"
        elif report_type == "qweb-text":
            report_name = "l10n_th_account_tax_report.report_withholding_tax_text"
        else:
            if self.company_id.wht_report_format == "rd" and report_type == "qweb-pdf":
                report_name = "l10n_th_account_tax_report.report_rd_withholding_tax"
            else:
                report_name = "l10n_th_account_tax_report.report_withholding_tax"
        return report_name, data
