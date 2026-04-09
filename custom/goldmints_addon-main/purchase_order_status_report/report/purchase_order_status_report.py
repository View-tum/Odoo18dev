from dataclasses import field
from odoo import models, _


class PurchaseOrderStatusReport(models.AbstractModel):
    _name = "report.purchase_order_status_report.po_status_report"
    _description = "Purchase Order Status QWeb Report"

    def _get_domain(self, wizard):
        # ใช้ company ปัจจุบันแทน field ใน wizard
        domain = [("company_id", "=", wizard.env.company.id)]

        if wizard.vendor_id:
            domain.append(("partner_id", "=", wizard.vendor_id.id))

        if wizard.date_from:
            domain.append(("date_order", ">=", wizard.date_from))
        if wizard.date_to:
            domain.append(("date_order", "<=", wizard.date_to))

        if wizard.state:
            domain.append(("state", "=", wizard.state))

        if wizard.invoice_status:
            domain.append(("invoice_status", "=", wizard.invoice_status))

        if wizard.product_id:
            domain.append(("order_line.product_id", "=", wizard.product_id.id))

        return domain

    def _get_lines(self, wizard):
        PurchaseOrder = self.env["purchase.order"]
        domain = self._get_domain(wizard)
        orders = PurchaseOrder.search(domain, order="date_order, name")

        lines = []
        for order in orders:
            for order_line in order.order_line:

                if wizard.product_id and order_line.product_id != wizard.product_id:
                    continue
                
                qty_received = order_line.qty_received
                
                # ดึงบรรทัดใบวางบิลที่ผูกกับ PO Line นี้ (ใช้ getattr เพื่อป้องกัน Error กรณีไม่มีโมดูล)
                bn_lines = getattr(order_line, "billing_note_line_ids", False)
                
                if bn_lines:
                    # คำนวณยอดที่อยู่ในใบวางบิลสถานะ Draft
                    qty_draft = sum(bn_lines.filtered(lambda l: l.billing_note_id.state == 'draft').mapped('quantity'))
                    # คำนวณยอดที่ยืนยันแล้ว (Confirmed, Partial Billed, Billed)
                    qty_confirmed = sum(bn_lines.filtered(lambda l: l.billing_note_id.state in ('confirmed', 'partial_billed', 'billed')).mapped('quantity'))
                    
                    # ตรรกะการให้สถานะ (ให้ความสำคัญกับยอดที่ Confirm แล้วก่อน)
                    if qty_confirmed >= qty_received - 0.001 and qty_received > 0:
                        bn_status = "fully"
                    elif qty_confirmed > 0:
                        bn_status = "partial" # ถ้ายืนยันแล้วบางส่วน ก็ถือว่าเป็น partial
                    elif qty_draft > 0:
                        bn_status = "draft"   # ถ้ายังไม่ยืนยันเลย แต่มี Draft อยู่ ให้เป็น draft
                    else:
                        bn_status = "no"
                else:
                    bn_status = "no"

                # ตรวจสอบว่าผู้ใช้ตั้ง Filter สถานะการวางบิลไว้หรือไม่ ถ้าไม่ตรงให้ข้ามบรรทัดนี้ไปเลย
                wiz_bn_status = getattr(wizard, "billing_note_status", False)
                if wiz_bn_status and bn_status != wiz_bn_status:
                    continue

                expected_arrival = getattr(order, "date_planned", False)

                line_dict = {
                    "order_id": order.id,
                    "order_name": order.name,
                    "order_url": f"/web#model=purchase.order&id={order.id}&view_type=form",

                    "company": order.company_id,
                    "vendor": order.partner_id,
                    "order_date": order.date_order.date() if order.date_order else "",
                    "expected_arrival": expected_arrival.date() if expected_arrival else "",

                    "state": order.state,
                    "invoice_status": order.invoice_status,
                    "billing_note_status": bn_status,

                    "product": order_line.product_id,
                    "description": order_line.name or "",
                    "qty": order_line.product_qty,
                    "qty_received": order_line.qty_received,
                    "qty_invoiced": order_line.qty_invoiced,
                    "qty_pending": order_line.product_qty - order_line.qty_received,
                    "qty_pending_invoice": order_line.qty_received - order_line.qty_invoiced,
                    "uom": order_line.product_uom,
                    "unit_price": order_line.price_unit,
                    "subtotal": order_line.price_subtotal,

                    "source_document": order.origin or "",
                }

                lines.append(line_dict)

        return lines

    def _get_report_values(self, docids, data=None):
        wizard = None
        if data and data.get("wizard_id"):
            wizard = self.env["purchase.order.status.report.wizard"].browse(
                data["wizard_id"]
            )
        elif docids:
            wizard = self.env["purchase.order.status.report.wizard"].browse(docids[0])

        if not wizard:
            return {}

        state_labels = {
            "draft": _("ใบขอเสนอราคา"),
            "sent": _("ส่งใบขอเสนอราคาแล้ว"),
            "to approve": _("รออนุมัติ"),
            "purchase": _("ใบสั่งซื้อ"),
            "done": _("ล็อกแล้ว"),
            "rejected": _("ปฏิเสธ"),
            "cancel": _("ยกเลิก"),
        }

        # 1. ปรับคำให้เป็น ตั้งหนี้
        invoice_labels = {
            "no": _("ยังไม่ตั้งหนี้"),
            "to invoice": _("รอตั้งหนี้"),
            "invoiced": _("ตั้งหนี้ครบแล้ว"),
        }

        # 2. เพิ่ม Label สำหรับสถานะการวางบิล
        billing_note_labels = {
            "no": _("ยังไม่วางบิล"),
            "draft": _("ร่างใบวางบิล"),
            "partial": _("วางบิลบางส่วน"),
            "fully": _("วางบิลครบแล้ว"),
        }

        lines = self._get_lines(wizard)
        company = wizard.env.company

        return {
            "doc_ids": [wizard.id],
            "doc_model": "purchase.order.status.report.wizard",
            "docs": [wizard],
            "wizard": wizard,
            "lines": lines,
            "company": company,
            "filters": {
                "vendor": wizard.vendor_id,
                "product": wizard.product_id,
                "date_from": wizard.date_from,
                "date_to": wizard.date_to,
                "state": wizard.state,
                "invoice_status": wizard.invoice_status,
                "billing_note_status": wizard.billing_note_status, # ส่งค่าที่ผู้ใช้กรองเข้าไปด้วย
            },
            "get_state_label": state_labels.get,
            "get_invoice_label": invoice_labels.get,
            "get_billing_note_label": billing_note_labels.get, # ส่งฟังก์ชันแปลภาษาเข้าไป
            "_": _,
        }
