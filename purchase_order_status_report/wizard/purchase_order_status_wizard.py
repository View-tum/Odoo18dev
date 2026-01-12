# purchase_order_status_report/wizard/purchase_order_status_wizard.py
from datetime import date
import io
import base64
import xlsxwriter
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PurchaseOrderStatusReportWizard(models.TransientModel):
    _name = "purchase.order.status.report.wizard"
    _description = "Purchase Order Status Report Wizard"

    # ไม่ให้เลือก company แล้ว ใช้ company ปัจจุบันจาก env.company
    # company = self.env.company

    vendor_id = fields.Many2one(
        "res.partner",
        string="Vendor",
        domain=[("supplier_rank", ">", 0)],
    )

    product_id = fields.Many2one(
        "product.product",
        string="Product",
        domain=[("purchase_ok", "=", True)],
    )

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

    # Order Status
    state = fields.Selection(
        [
            ("draft", "RFQ"),
            ("sent", "RFQ Sent"),
            ("to approve", "To Approve"),
            ("purchase", "Purchase Order"),
            ("done", "Locked"),
            ("rejected", "Rejected"),
            ("cancel", "Cancelled"),
        ],
        string="Order Status",
    )

    # Billing Status
    invoice_status = fields.Selection(
        [
            ("no", "Nothing to Bill"),
            ("to invoice", "Waiting Bills"),
            ("invoiced", "Fully Billed"),
        ],
        string="Billing Status",
    )

    @api.constrains("date_from", "date_to")
    def _check_date_range(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_from > rec.date_to:
                raise ValidationError(_("Start Date must not be after End Date."))

    # ---------- Helpers ----------

    def _get_report_base_filename(self):
        self.ensure_one()
        name = _("PO Status")
        if self.date_from and self.date_to:
            name += f" {self.date_from} - {self.date_to}"
        return name

    def _prepare_report_data(self):
        self.ensure_one()
        return {
            "wizard_id": self.id,
            # company ใช้ env.company ไม่ต้องส่ง id มา
            "vendor_id": self.vendor_id.id if self.vendor_id else False,
            "product_id": self.product_id.id if self.product_id else False,
            "date_from": self.date_from,
            "date_to": self.date_to,
            "state": self.state,
            "invoice_status": self.invoice_status,
        }

    def _report_action(self, report_xmlid, report_type="qweb-pdf"):
        self.ensure_one()
        action = self.env.ref(report_xmlid).report_action(
            self,
            data=self._prepare_report_data(),
        )
        action["report_type"] = report_type
        return action

    # ---------- Buttons ----------

    def button_export_html(self):
        return self._report_action(
            "purchase_order_status_report.action_report_purchase_order_status",
            "qweb-html",
        )

    def button_export_pdf(self):
        return self._report_action(
            "purchase_order_status_report.action_report_purchase_order_status",
            "qweb-pdf",
        )

    def button_export_xlsx(self):
        """Export XLSX แบบเดียวกับ PR: สร้างไฟล์เอง + ตั้งชื่อไฟล์เอง"""
        self.ensure_one()

        # 1) เตรียม buffer + workbook (เหมือน cost_sheet / PR)
        bio = io.BytesIO()
        workbook = xlsxwriter.Workbook(bio, {"in_memory": True})

        # 2) reuse logic จาก AbstractModel XLSX
        #    ใช้ generate_xlsx_report ที่เขียนไว้แล้ว
        report_model = self.env[
            "report.purchase_order_status_report.po_status_report_xlsx"
        ]

        # generate_xlsx_report ของรายงาน PO browse wizard จาก data['wizard_id']
        data = {"wizard_id": self.id}
        report_model.generate_xlsx_report(workbook, data, self)

        # 3) ปิด workbook แล้วดึงค่า binary
        workbook.close()
        xlsx_data = bio.getvalue()
        bio.close()

        # 4) ตั้งชื่อไฟล์แบบเดียวกับ PR
        #    base name มาจาก _get_report_base_filename() เช่น "PO Status 2025-11-01 - 2025-11-27"
        filename = f"{self._get_report_base_filename()}.xlsx"

        # 5) สร้าง attachment แล้วส่งเป็น act_url (เหมือน PR / cost_sheet)
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
