from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

# 1. แทรกฟิลด์ Checkbox ลงในบรรทัดตาราง
class PurchaseOrderStatusReportWizardLine(models.TransientModel):
    _inherit = "purchase.order.status.report.wizard.line"

    is_selected = fields.Boolean(string=" ")

# 2. เพิ่มฟังก์ชันปุ่มลงใน Wizard หลัก
class PurchaseOrderStatusReportWizard(models.TransientModel):
    _inherit = "purchase.order.status.report.wizard"

    has_selected_lines = fields.Boolean(
        compute="_compute_has_selected_lines"
    )

    @api.depends("line_ids.is_selected")
    def _compute_has_selected_lines(self):
        for wiz in self:
            # ถ้ามีบรรทัดไหน is_selected เป็น True จะทำให้ฟิลด์นี้เป็น True ทันที
            wiz.has_selected_lines = any(wiz.line_ids.mapped("is_selected"))

    def action_create_billing_note(self):
        self.ensure_one()
        selected_lines = self.line_ids.filtered(lambda l: l.is_selected)
        if not selected_lines:
            raise ValidationError(_("กรุณาเลือกรายการอย่างน้อย 1 รายการ"))

        unique_pos = selected_lines.mapped("order_id")

        if len(unique_pos.mapped("partner_id")) > 1:
            raise ValidationError(_("ไม่สามารถสร้างใบวางบิลรวมกันจากผู้ขาย (Vendor) หลายรายได้ กรุณาเลือกรายการที่เป็นผู้ขายเดียวกัน"))

        invalid_state_pos = unique_pos.filtered(lambda po: po.state not in ['purchase', 'done'])
        if invalid_state_pos:
            raise ValidationError(_("มีบางรายการที่ยังไม่ได้ยืนยันเป็นใบสั่งซื้อ (หรือถูกยกเลิกไปแล้ว) กรุณาตรวจสอบอีกครั้ง"))

        return unique_pos.action_create_consolidated_billing_note()