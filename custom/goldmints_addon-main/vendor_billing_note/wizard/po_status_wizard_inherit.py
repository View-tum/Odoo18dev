from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

# 1. เพิ่มฟังก์ชันปุ่มลงใน Wizard หลัก
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
        selected_lines = self.line_ids.filtered(lambda l: l.is_selected and l.is_billable)
        if not selected_lines:
            raise ValidationError(_("กรุณาเลือกรายการอย่างน้อย 1 รายการที่สามารถวางบิลได้"))

        # Check vendor consistency
        if len(selected_lines.mapped("vendor_id")) > 1:
            raise ValidationError(_("ไม่สามารถสร้างใบวางบิลรวมกันจากผู้ขาย (Vendor) หลายรายได้ กรุณาเลือกรายการที่เป็นผู้ขายเดียวกัน"))

        billing_data = []
        
        # Group selected lines by PO Line ID
        po_line_ids = selected_lines.mapped('po_line_id')
        
        for po_line in po_line_ids:
            po_line_selected = selected_lines.filtered(lambda l: l.po_line_id == po_line)
            header_line = po_line_selected.filtered(lambda l: l.is_header)
            detail_lines = po_line_selected.filtered(lambda l: not l.is_header)
            
            if detail_lines:
                # If detail lines are selected, we bill only those specific receipts
                for detail in detail_lines:
                    billing_data.append({
                        'purchase_line_id': po_line.id,
                        'quantity': detail.qty_received,
                        'picking_id': detail.picking_id.id if detail.picking_id else False,
                        'service_acceptance_id': detail.service_acceptance_id.id if detail.service_acceptance_id else False,
                    })
            elif header_line:
                # If only the header is selected, we bill the remaining quantity for this PO line
                qty_to_bill = po_line.qty_received - po_line.qty_billing_noted
                if qty_to_bill > 0.001:
                    billing_data.append({
                        'purchase_line_id': po_line.id,
                        'quantity': qty_to_bill,
                    })

        if not billing_data:
            raise ValidationError(_("รายการที่เลือกไม่มีจำนวนที่สามารถวางบิลได้"))

        return self.env['purchase.order'].action_create_billing_note_from_data(
            selected_lines[0].vendor_id.id, 
            billing_data
        )