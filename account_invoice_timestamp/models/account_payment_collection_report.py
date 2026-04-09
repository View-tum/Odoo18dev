# -*- coding: utf-8 -*-
from odoo import models, fields
from odoo.exceptions import UserError


class PaymentCollectionReport(models.TransientModel):
    _inherit = "account.payment.collection.report"

    def action_print_pdf(self):
        """
        TH: (Override) สืบทอดฟังก์ชันการพิมพ์รายงานเพื่อเพิ่มกระบวนการบันทึก Log (Timestamp) ระบบจะค้นหาใบแจ้งหนี้ตามเงื่อนไข ตรวจสอบว่าเคยถูกบันทึกแล้วหรือไม่ และสร้างรายการ Log ใหม่เฉพาะใบแจ้งหนี้ที่ยังไม่เคยมีประวัติเท่านั้น
        EN: (Override) Inherits the print report function to add a Timestamp Logging process. The system searches for invoices based on criteria, checks for existing logs, and creates new log entries only for invoices that have not been recorded yet.
        """
        res = super(PaymentCollectionReport, self).action_print_pdf()

        domain = [
            ("move_type", "=", "out_invoice"),
            ("state", "not in", ["draft", "cancel"]),
            (
                "payment_state",
                "not in",
                [
                    "paid",
                    "reversed",
                    "partial",
                    "blocked",
                    "invoicing_legacy",
                    "draft",
                    "cancel",
                ],
            ),
        ]

        if self.date_from:
            domain.append(("invoice_date", ">=", self.date_from))
        if self.date_to:
            domain.append(("invoice_date", "<=", self.date_to))

        if self.customer_ids and not self.subregion_ids:
            domain.append(("partner_id", "in", self.customer_ids.ids))
        elif not self.customer_ids and self.subregion_ids:
            partners = self.env["res.partner"].search(
                [("subregion_id", "in", self.subregion_ids.ids)]
            )
            if partners:
                domain.append(("partner_id", "in", partners.ids))
            else:
                domain.append(("id", "=", False))
        else:
            domain.append(("id", "=", False))

        candidate_invoices = self.env["account.move"].search(domain)

        if candidate_invoices:
            existing_logs = (
                self.env["account.invoice.timestamp"]
                .sudo()
                .search([("invoice_ids", "in", candidate_invoices.ids)])
            )
            already_logged_invoice_ids = existing_logs.mapped("invoice_ids").ids
            candidate_invoice_ids_set = set(candidate_invoices.ids)
            already_logged_invoice_ids_set = set(already_logged_invoice_ids)
            new_invoice_ids_to_log = list(
                candidate_invoice_ids_set - already_logged_invoice_ids_set
            )

            if new_invoice_ids_to_log:
                try:
                    self.env["account.invoice.timestamp"].sudo().create(
                        {
                            "timestamp": fields.Datetime.now(),
                            "user_id": self.env.user.id,
                            "invoice_ids": [(6, 0, new_invoice_ids_to_log)],
                        }
                    )
                except Exception as e:
                    raise UserError(f"Cannot save print log due to: {e}")

        return res
