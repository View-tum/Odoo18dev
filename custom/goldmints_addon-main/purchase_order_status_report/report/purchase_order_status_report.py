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
            # 1. Pre-calculate billed receipts for this PO
            BilledLines = self.env['vendor.billing.note.line'].search([
                ('purchase_order_id', '=', order.id),
                ('billing_note_id.state', '!=', 'cancel')
            ])
            billed_sa_ids = BilledLines.mapped('service_acceptance_id').ids

            # 2. Sum PO-level metrics across all lines matching product filter
            total_qty_received = 0.0
            total_qty_invoiced = 0.0
            total_subtotal = 0.0
            is_billable_overall = False
            is_already_billed_overall = True
            products = set()

            for order_line in order.order_line:
                if wizard.product_id and order_line.product_id != wizard.product_id:
                    continue
                products.add(order_line.product_id.display_name or '')
                total_qty_received += order_line.qty_received
                total_qty_invoiced += order_line.qty_invoiced
                total_subtotal += order_line.price_subtotal

                # Check billable status for this line
                qty_to_billing_note = (
                    order_line._get_qty_to_billing_note()
                    if hasattr(order_line, "_get_qty_to_billing_note")
                    else max(order_line.qty_received - order_line.qty_billing_noted, 0.0)
                )
                qty_billing_basis = (
                    order_line._get_billing_note_qty_basis()
                    if hasattr(order_line, "_get_billing_note_qty_basis")
                    else order_line.qty_received
                )

                if qty_to_billing_note > 0.001:
                    is_billable_overall = True
                if order_line.qty_billing_noted < qty_billing_basis - 0.001 and qty_billing_basis > 0:
                    is_already_billed_overall = False

            if not products:
                continue
            elif len(products) > 1:
                product_display = "หลายรายการ"
            else:
                product_display = list(products)[0]

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
                "description": "",
                "source_document": order.origin or "",
                "po_line_id": False,
            }

            apds = order.invoice_ids.filtered(lambda m: m.move_type == 'in_invoice' and m.state != 'cancel')
            cns = order.invoice_ids.filtered(lambda m: m.move_type == 'in_refund' and m.state != 'cancel')
            inv_ref_parts = []
            if apds:
                inv_ref_parts.append(f"APD: {', '.join(str(n) for n in apds.mapped('name') if n)}")
            if cns:
                inv_ref_parts.append(f"CN: {', '.join(str(n) for n in cns.mapped('name') if n)}")
            inv_ref_display = " | ".join(inv_ref_parts)

            header = base_dict.copy()
            header.update({
                "is_header": True,
                "product": False,
                "product_display": product_display,
                "uom": False,
                "unit_price": 0.0,
                "qty": 0.0,
                "qty_received": total_qty_received,
                "qty_invoiced": total_qty_invoiced,
                "qty_pending": 0.0,
                "qty_pending_invoice": total_qty_received - total_qty_invoiced,
                "receipt_ref": _("Total Summary"),
                "receipt_date": False,
                "inv_ref": inv_ref_display,
                "is_pending": False,
                "subtotal": total_subtotal,
                "is_billable": is_billable_overall,
                "is_already_billed": is_already_billed_overall if (total_qty_received > 0 or is_billable_overall) else False,
                "billing_note_status": 'fully' if is_already_billed_overall and (total_qty_received > 0 or is_billable_overall) else 'no',
            })
            lines.append(header)

            # --- B. Detail Rows (Only Service Acceptance documents) ---
            # Find unique Service Acceptance (SA) documents linked to this PO's lines
            ServiceAcceptanceLine = self.env.get('service.acceptance.line')
            if ServiceAcceptanceLine is not None:
                sa_lines = ServiceAcceptanceLine.search([
                    ('po_line_id', 'in', order.order_line.ids),
                    ('acceptance_id.state', '=', 'done')
                ])
                # Group by acceptance_id
                unique_sas = sa_lines.mapped('acceptance_id')
                for sa in unique_sas:
                    # Filter lines of this specific SA
                    sa_detail_lines = sa_lines.filtered(lambda l: l.acceptance_id == sa)
                    
                    # Sum metrics for this SA row
                    sa_qty_received = sum(l.qty_accepted for l in sa_detail_lines)
                    sa_subtotal = sum(l.qty_accepted * l.po_line_id.price_unit for l in sa_detail_lines)
                    
                    sa_products = set(l.product_id.display_name or '' for l in sa_detail_lines)
                    if len(sa_products) > 1:
                        sa_product_display = "หลายรายการ"
                        sa_uom = False
                        sa_price = 0.0
                    elif sa_products:
                        sa_product_display = list(sa_products)[0]
                        sa_uom = sa_detail_lines[0].product_uom
                        sa_price = sa_detail_lines[0].price_unit
                    else:
                        sa_product_display = ""
                        sa_uom = False
                        sa_price = 0.0

                    is_already_billed = sa.id in billed_sa_ids

                    d_row = base_dict.copy()
                    d_row.update({
                        "is_header": False,
                        "po_line_id": sa_detail_lines[0].po_line_id.id if sa_detail_lines else False,
                        "product": sa_detail_lines[0].product_id if sa_detail_lines else False,
                        "product_display": sa_product_display,
                        "uom": sa_uom,
                        "unit_price": sa_price,
                        "qty": 0.0,
                        "qty_received": sa_qty_received,
                        "qty_pending_invoice": sa_qty_received,
                        "receipt_ref": f"↳ ✅ {sa.name}",
                        "receipt_date": sa.date,
                        "inv_ref": getattr(sa, 'invoice_ref', '') or "",
                        "picking_id": False,
                        "service_acceptance_id": sa.id,
                        "is_pending": False,
                        "subtotal": sa_subtotal,
                        "is_billable": not is_already_billed,
                        "is_already_billed": is_already_billed,
                        "billing_note_status": 'fully' if is_already_billed else 'no',
                    })
                    lines.append(d_row)

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
