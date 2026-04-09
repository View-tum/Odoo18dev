from odoo import models, fields, api


class ChequeReport(models.TransientModel):
    _name = "cheque.report"
    _description = "Cheque Report"

    cheque_ids = fields.Many2many(
        comodel_name="cheque.inbound.outbound",
        string="Cheque",
        default=lambda self: self.env.context.get("active_ids"),
    )
    cheque_date = fields.Date(string="Cheque Date", help="(365 custom) วันที่ของเช็ค.")
    report_id = fields.Many2one(
        comodel_name="jasper.report",
        domain=[("model_id", "=", _name)],
        string="Report",
        help="(365 custom) เทมเพลตรายงานที่จะใช้ในการสร้างเอกสาร (เลือกโดยระบบตามการตั้งค่า).",
    )

    @api.model
    def default_get(self, fields_list):
        """Initialize default values for cheque_date and report template."""
        res = super(ChequeReport, self).default_get(fields_list)

        if "cheque_date" in fields_list and not res.get("cheque_date"):
            res["cheque_date"] = fields.Date.context_today(self)

        if "report_id" in fields_list and not res.get("report_id"):
            found_report = self.env["jasper.report"].search(
                [("model_id", "=", self._name)], order="id", limit=1
            )
            if found_report:
                res["report_id"] = found_report.id

        return res

    def action_print(self):
        """Logic สำหรับการสั่งพิมพ์ Report"""
        self.ensure_one()

        if not self.report_id:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "การตั้งค่าไม่ถูกต้อง",
                    "message": "  • ไม่พบรายงาน กรุณาเลือกรายงาน",
                    "type": "warning",
                    "sticky": False,
                },
            }

        cheque_ids = (
            ",".join(map(str, self.cheque_ids.ids)) if self.cheque_ids else None
        )
        cheque_date = (
            self.cheque_date.strftime("%Y-%m-%d") if self.cheque_date else None
        )

        data = {
            "cheque_ids": cheque_ids,
            "cheque_date": cheque_date,
        }

        return self.report_id.run_report(docids=[self.ids[0]], data=data)
