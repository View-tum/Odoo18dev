# purchase_request_status_report/wizard/purchase_request_status_wizard.py
from datetime import date, datetime
import io
import base64
import xlsxwriter
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PurchaseRequestStatusReportWizard(models.TransientModel):
    _name = "purchase.request.status.report.wizard"
    _description = "Purchase Request Status Report Wizard"

    # 1) บริษัท
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
    )

    # 2) ผู้ขาย
    vendor_id = fields.Many2one(
        "res.partner",
        string="Vendor",
        domain=[("supplier_rank", ">", 0)],
    )

    # 3) สินค้า
    product_id = fields.Many2one(
        "product.product",
        string="Product",
        domain=[("purchase_ok", "=", True)],
    )

    # 4-5) วันที่เริ่มต้น/สิ้นสุด
    date_from = fields.Date(
        string="Start Date",
        required=True,
        default=lambda self: date.today().replace(day=1),
    )
    date_to = fields.Date(
        string="End Date",
        required=True,
        default=lambda self: date.today(),
    )

    # 6) สถานะเอกสาร
    state = fields.Selection(
        [
            ("draft", "PR"),
            ("pr_approval_lvl1", "PR_Approval_Lv1"),
            ("pr_approval_lvl2", "PR_Approval_Lv2"),
            ("approved", "Approved"),
            ("in_progress", "In Progress"),
            ("done", "Done"),
            ("rejected", "Rejected"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
    )

    @api.constrains("date_from", "date_to")
    def _check_date_range(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_from > rec.date_to:
                raise ValidationError(_("Start Date must not be after End Date."))

    # ---- Helpers for report ----

    def _get_report_base_filename(self):
        """ชื่อไฟล์เวลา export XLSX/PDF"""
        self.ensure_one()
        name = _("PR Status")
        if self.date_from and self.date_to:
            name += f" {self.date_from} - {self.date_to}"
        return name

    def _prepare_report_data(self):
        self.ensure_one()
        return {
            "wizard_id": self.id,
            "company_id": self.company_id.id,
            "vendor_id": self.vendor_id.id if self.vendor_id else False,
            "product_id": self.product_id.id if self.product_id else False,
            "date_from": self.date_from,
            "date_to": self.date_to,
            "state": self.state,
        }

    def _report_action(self, report_xmlid, report_type="qweb-pdf"):
        """เรียก ir.actions.report เหมือน cost_sheet"""
        self.ensure_one()
        action = self.env.ref(report_xmlid).report_action(
            self,
            data=self._prepare_report_data(),
        )
        action["report_type"] = report_type
        return action

    # ==== ปุ่มบน wizard ====

    def button_export_html(self):
        """Preview HTML (ใช้ action เดียวกับ PDF)"""
        return self._report_action(
            "purchase_request_status_report.action_report_purchase_request_status",
            "qweb-html",
        )

    def button_export_pdf(self):
        """Export PDF (ใช้ paperformat)"""
        return self._report_action(
            "purchase_request_status_report.action_report_purchase_request_status",
            "qweb-pdf",
        )

    def button_export_xlsx(self):
        """Export XLSX แบบ cost_sheet: สร้างไฟล์เอง + ตั้งชื่อไฟล์เอง"""
        self.ensure_one()

        # 1) เตรียม buffer + workbook (เหมือน cost_sheet)
        bio = io.BytesIO()
        workbook = xlsxwriter.Workbook(bio, {"in_memory": True})

        # 2) reuse logic จาก AbstractModel XLSX
        #    ใช้ generate_xlsx_report ที่คุณเขียนไว้แล้ว
        report_model = self.env[
            "report.purchase_request_status_report.pr_status_report_xlsx"
        ]

        # generate_xlsx_report ของคุณ browse wizard จาก data['wizard_id']
        data = {"wizard_id": self.id}
        report_model.generate_xlsx_report(workbook, data, self)

        # 3) ปิด workbook แล้วดึงค่า binary
        workbook.close()
        xlsx_data = bio.getvalue()
        bio.close()

        # 4) ตั้งชื่อไฟล์แบบที่ต้องการ
        #    ถ้าอยากเหมือน cost_sheet เป๊ะ ๆ (มี timestamp)
        # filename = "%s_%s.xlsx" % (
        #     self._get_report_base_filename().replace(" ", "_"),
        #     datetime.now().strftime("%Y%m%d_%H%M%S"),
        # )
        # ถ้าอยากสั้น ๆ แค่ชื่อรายงาน: ก็ใช้
        filename = f"{self._get_report_base_filename()}.xlsx"

        # 5) สร้าง attachment แล้วส่งเป็น act_url (เหมือน cost_sheet)
        att = self.env["ir.attachment"].create({
            "name": filename,
            "type": "binary",
            "datas": base64.b64encode(xlsx_data),
            "res_model": self._name,
            "res_id": self.id,
            "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "public": False,
        })

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{att.id}?download=true",
            "target": "self",
        }
