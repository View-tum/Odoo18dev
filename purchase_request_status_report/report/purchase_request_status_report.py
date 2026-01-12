# purchase_request_status_report/report/purchase_request_status_report.py
from odoo import models, _


class PurchaseRequestStatusReport(models.AbstractModel):
    _name = "report.purchase_request_status_report.pr_status_report"
    _description = "Purchase Request Status QWeb Report"

    def _get_domain(self, wizard):
        """สร้าง domain จากเงื่อนไขใน wizard"""
        domain = [("company_id", "=", wizard.company_id.id)]

        if wizard.vendor_id:
            # Field tooltip ในรูปคือ field: vendor
            domain.append(("vendor", "=", wizard.vendor_id.id))

        if wizard.state:
            domain.append(("state", "=", wizard.state))

        if wizard.date_from:
            domain.append(("date_start", ">=", wizard.date_from))
        if wizard.date_to:
            domain.append(("date_start", "<=", wizard.date_to))

        return domain

    def _get_lines(self, wizard):
        """คืนค่า list ของ line ที่จะใช้แสดงในรายงาน"""
        PurchaseRequest = self.env["purchase.request"]
        PurchaseRequestLine = self.env["purchase.request.line"]

        domain = self._get_domain(wizard)
        requests = PurchaseRequest.search(domain, order="date_start, id")

        lines = []
        for req in requests:
            # ถ้ามี filter สินค้า → เลือกเฉพาะ line ของสินค้านั้น
            line_domain = [("request_id", "=", req.id)]
            if wizard.product_id:
                line_domain.append(("product_id", "=", wizard.product_id.id))
            pr_lines = PurchaseRequestLine.search(line_domain)

            for line in pr_lines:
                line_state = req.state
                if req.state not in ("draft", "cancel", "rejected"):
                    po_lines = line.purchase_lines.filtered(
                        lambda l: l.state != "cancel"
                    )

                    if po_lines:
                        invoices = po_lines.mapped("invoice_lines.move_id").filtered(
                            lambda inv: inv.move_type == "in_invoice"
                            and inv.state == "posted"
                        )
                        if invoices and all(
                            inv.payment_state in ("paid", "in_payment")
                            for inv in invoices
                        ):
                            line_state = "done"
                        elif any(
                            po.state in ("purchase", "done")
                            for po in po_lines.mapped("order_id")
                        ):
                            line_state = "in_progress"
                        elif any(
                            po.state in ("draft", "sent")
                            for po in po_lines.mapped("order_id")
                        ):
                            line_state = "approved"

                lines.append(
                    {
                        "request": req,
                        "line": line,
                        "company": req.company_id,
                        "vendor": req.vendor,
                        "request_name": req.name,
                        "request_date": req.date_start,
                        "state": line_state,
                        "product": line.product_id,
                        "description": line.name or line.description or "",
                        "qty": line.product_qty,
                        "uom": line.product_uom_id,
                        "estimated_cost": line.estimated_cost,
                    }
                )
        return lines

    def _get_report_values(self, docids, data=None):
        wizard = None
        if data and data.get("wizard_id"):
            wizard = self.env["purchase.request.status.report.wizard"].browse(
                data["wizard_id"]
            )
        elif docids:
            wizard = self.env["purchase.request.status.report.wizard"].browse(docids[0])

        if not wizard:
            return {}

        lines = self._get_lines(wizard)

        # --- แก้ตรงนี้ ---
        field_state = self.env["purchase.request"]._fields["state"]
        selection = field_state.selection
        # ถ้าเป็นฟังก์ชัน → เรียกให้คืนค่า list ของ (value, label)
        if callable(selection):
            selection = selection(self.env["purchase.request"])
        state_labels = dict(selection)
        # --- จบส่วนที่เพิ่ม ---

        return {
            "doc_ids": [],
            "doc_model": "purchase.request",
            "docs": [wizard],
            "wizard": wizard,
            "lines": lines,
            "company": wizard.company_id,
            "filters": {
                "vendor": wizard.vendor_id,
                "product": wizard.product_id,
                "date_from": wizard.date_from,
                "date_to": wizard.date_to,
                "state": wizard.state,
            },
            "get_state_label": state_labels.get,  # ใช้ dict.get ตามเดิม
            "_": _,
        }
