from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = "sale.order"

    is_printed = fields.Boolean(
        string="Is Printed",
        default=False,
        copy=False,
        help="(365 custom) สถานะพิมพ์แล้ว เพื่อให้ปุ่มเปลี่ยนเป็นสีเทา",
    )
    has_posted_invoice = fields.Boolean(
        string="Has Posted Invoice",
        compute="_compute_has_posted_invoice",
        store=False,
        help="(365 custom) คำนวณว่า Sale Order มี Invoice ที่เป็นสถานะ 'posted' หรือไม่",
    )

    @api.depends("invoice_ids", "invoice_ids.state")
    def _compute_has_posted_invoice(self):
        """คำนวณว่า Sale Order มี Invoice ที่เป็นสถานะ 'posted' หรือไม่"""
        for order in self:
            posted_invoices = order.invoice_ids.filtered(
                lambda inv: inv.state == "posted"
            )
            order.has_posted_invoice = bool(posted_invoices)

    def action_print_to_jasper(self):
        """ฟังก์ชันสำหรับปุ่มกดส่งข้อมูลไป Jasper"""
        self.ensure_one()

        target_sequence = "2" if self.is_printed else "1"

        config = self.env["sale.tax.invoice.config"].search(
            [("sequence", "=", target_sequence)], limit=1
        )

        if not config or not config.report_id:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "ไม่พบการตั้งค่ารายงาน",
                    "message": f"กรุณาตั้งค่าสำหรับลำดับการพิมพ์ที่ {target_sequence} ในหน้าตั้งค่า",
                    "type": "warning",
                    "sticky": False,
                },
            }

        # print("#" * 50)  # Debug log separator
        # print("Configuration found for sequence:", target_sequence)  # Debug log
        # print("Running report with ID:", config.report_id.id)  # Debug log
        # print("Sale Order ID:", self.id)  # Debug log
        # print("#" * 50)  # Debug log separator

        if not self.is_printed:
            self.is_printed = True

        return config.report_id.run_report(self.ids)
