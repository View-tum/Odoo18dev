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
                
                qty_received_total = order_line.qty_received
                qty_invoiced_total = order_line.qty_invoiced
                
                # 1. Billing Note Status (Overall for the PO Line)
                bn_lines = getattr(order_line, "billing_note_line_ids", False)
                bn_status_overall = "no"
                if bn_lines:
                    qty_draft = sum(bn_lines.filtered(lambda l: l.billing_note_id.state == 'draft').mapped('quantity'))
                    qty_confirmed = sum(bn_lines.filtered(lambda l: l.billing_note_id.state in ('confirmed', 'partial_billed', 'billed')).mapped('quantity'))
                    
                    if qty_confirmed >= qty_received_total - 0.001 and qty_received_total > 0:
                        bn_status_overall = "fully"
                    elif qty_confirmed > 0:
                        bn_status_overall = "partial"
                    elif qty_draft > 0:
                        bn_status_overall = "draft"

                # Filter by billing note status if requested
                wiz_bn_status = getattr(wizard, "billing_note_status", False)
                if wiz_bn_status and bn_status_overall != wiz_bn_status:
                    continue

                # Prepare Base Data
                expected_arrival = getattr(order, "date_planned", False)
                base_dict = {
                    "order_id": order.id,
                    "order_name": order.name,
                    "order_url": f"/web#model=purchase.order&id={order.id}&view_type=form",
                    "company": order.company_id,
                    "vendor": order.partner_id,
                    "order_date": order.date_order.date() if order.date_order else "",
                    "expected_arrival": expected_arrival.date() if expected_arrival else "",
                    "state": order.state,
                    "invoice_status": order.invoice_status,
                    "product": order_line.product_id,
                    "description": order_line.name or "",
                    "uom": order_line.product_uom,
                    "unit_price": order_line.price_unit,
                    "source_document": order.origin or "",
                    "billing_note_status": bn_status_overall,
                    "po_line_id": order_line.id,
                }

                # Collect Detailed Receipt/SA Lines
                detail_lines_data = []
                
                # A. From Stock Picking
                for move in order_line.move_ids.filtered(lambda m: m.state == 'done' and m.picking_id):
                    detail_lines_data.append({
                        "qty_received": move.quantity,
                        "receipt_ref": f"📦 {move.picking_id.name}",
                        "receipt_date": move.picking_id.date_done.date() if move.picking_id.date_done else False,
                        "inv_ref": getattr(move.picking_id, 'invoice_reference', '') or "",
                        "picking_id": move.picking_id.id,
                    })

                # B. From Service Acceptance
                ServiceAcceptanceLine = self.env.get('service.acceptance.line')
                if ServiceAcceptanceLine:
                    sa_lines = ServiceAcceptanceLine.search([
                        ('po_line_id', '=', order_line.id),
                        ('acceptance_id.state', '=', 'done')
                    ])
                    for sa_line in sa_lines:
                        detail_lines_data.append({
                            "qty_received": sa_line.qty_accepted,
                            "receipt_ref": f"✅ {sa_line.acceptance_id.name}",
                            "receipt_date": sa_line.acceptance_id.date,
                            "inv_ref": getattr(sa_line.acceptance_id, 'invoice_ref', '') or "",
                            "service_acceptance_id": sa_line.acceptance_id.id,
                        })

                # --- 1. Master Header Row ---
                header = base_dict.copy()
                header_is_billable = (order_line.qty_received - order_line.qty_billing_noted) > 0.001
                header.update({
                    "is_header": True,
                    "qty": order_line.product_qty,
                    "qty_received": order_line.qty_received,
                    "qty_invoiced": order_line.qty_invoiced,
                    "qty_pending": order_line.product_qty - order_line.qty_received,
                    "qty_pending_invoice": order_line.qty_received - order_line.qty_invoiced,
                    "receipt_ref": _("Total Summary"),
                    "receipt_date": False,
                    "inv_ref": "",
                    "is_pending": False,
                    "subtotal": order_line.price_subtotal,
                    "is_billable": header_is_billable,
                    "is_already_billed": order_line.qty_billing_noted >= order_line.qty_received - 0.001 if order_line.qty_received > 0 else False,
                })
                lines.append(header)

                # --- 2. Detail Rows (Receipts) ---
                remaining_invoiced = qty_invoiced_total
                
                # Pre-calculate billed receipts for this PO line
                BilledLines = self.env['vendor.billing.note.line'].search([
                    ('purchase_line_id', '=', order_line.id),
                    ('billing_note_id.state', '!=', 'cancel')
                ])
                billed_picking_ids = BilledLines.mapped('picking_id').ids
                billed_sa_ids = BilledLines.mapped('service_acceptance_id').ids

                for detail in detail_lines_data:
                    d_row = base_dict.copy()
                    
                    # Distribute Invoiced Qty (FIFO)
                    current_received = detail['qty_received']
                    current_invoiced = min(remaining_invoiced, current_received) if current_received > 0 else 0.0
                    remaining_invoiced -= current_invoiced
                    
                    p_id = detail.get('picking_id')
                    sa_id = detail.get('service_acceptance_id')
                    
                    is_already_billed = False
                    if p_id and p_id in billed_picking_ids:
                        is_already_billed = True
                    elif sa_id and sa_id in billed_sa_ids:
                        is_already_billed = True

                    d_row.update({
                        "is_header": False,
                        "qty": 0.0,
                        "qty_received": current_received,
                        "qty_invoiced": current_invoiced,
                        "qty_pending": 0.0,
                        "qty_pending_invoice": current_received - current_invoiced,
                        "receipt_ref": f"↳ {detail['receipt_ref']}",
                        "receipt_date": detail['receipt_date'],
                        "inv_ref": detail['inv_ref'],
                        "picking_id": p_id,
                        "service_acceptance_id": sa_id,
                        "is_pending": False,
                        "subtotal": 0.0,
                        "is_billable": not is_already_billed,
                        "is_already_billed": is_already_billed,
                    })
                    lines.append(d_row)

                # --- 3. Pending Row (if any balance) ---
                total_receipt_qty = sum(d['qty_received'] for d in detail_lines_data)
                if order_line.product_qty > total_receipt_qty + 0.001:
                    pending_qty = order_line.product_qty - total_receipt_qty
                    p_row = base_dict.copy()
                    p_row.update({
                        "is_header": False,
                        "qty": 0.0,
                        "qty_received": 0.0,
                        "qty_invoiced": 0.0,
                        "qty_pending": pending_qty,
                        "qty_pending_invoice": 0.0,
                        "receipt_ref": f"↳ {_('🕒 Pending Balance')}",
                        "receipt_date": False,
                        "inv_ref": "",
                        "is_pending": True,
                        "subtotal": 0.0,
                        "is_billable": False,
                        "is_already_billed": False,
                    })
                    lines.append(p_row)

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
