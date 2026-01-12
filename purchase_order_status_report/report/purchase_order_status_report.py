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
            for line in order.order_line:
                if wizard.product_id and line.product_id != wizard.product_id:
                    continue
                expected_arrival = getattr(order, "date_planned", False) or False
                lines.append(
                    {
                        "order": order,
                        "line": line,
                        "company": order.company_id,
                        "vendor": order.partner_id,
                        "order_name": order.name,
                        "order_date": order.date_order.date()
                        if order.date_order
                        else "",
                        "expected_arrival": expected_arrival.date()
                        if expected_arrival
                        else "",
                        "state": order.state,
                        "invoice_status": order.invoice_status,
                        "product": line.product_id,
                        "description": line.name or "",
                        "qty": line.product_qty,
                        "uom": line.product_uom,
                        "unit_price": line.price_unit,
                        "subtotal": line.price_subtotal,
                        "source_document": order.origin or "",
                    }
                )
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

        invoice_labels = {
            "no": _("ยังไม่ต้องวางบิล"),
            "to invoice": _("รอวางบิล"),
            "invoiced": _("วางบิลครบแล้ว"),
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
            },
            "get_state_label": state_labels.get,
            "get_invoice_label": invoice_labels.get,
            "_": _,
        }
