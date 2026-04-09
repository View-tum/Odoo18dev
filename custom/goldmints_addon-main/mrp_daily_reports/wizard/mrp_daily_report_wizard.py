from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date


class MrpDailyReportWizard(models.TransientModel):
    _name = "mrp.daily.report.wizard"
    _description = "MRP Daily Report Wizard"

    # =====================
    # Report Selector (Many2one)
    # =====================
    report_id = fields.Many2one(
        comodel_name="jasper.report",
        string="ประเภทรายงาน",
        required=True,
        domain=[("model_id", "=", "mrp.daily.report.wizard")],
        help="เลือกระบุรายงาน Jasper ที่ต้องการ",
    )

    # =====================
    # All Filters (Always Visible)
    # =====================
    date_from = fields.Date(
        string="Date From",
        required=True,
        default=lambda self: date.today().replace(day=1),
    )
    date_to = fields.Date(
        string="Date To", required=True, default=lambda self: date.today()
    )

    factory_tag_ids = fields.Many2many(
        comodel_name="mrp.workcenter.tag",
        string="Factory Type",
        required=True,
        help="Select factory type such as Drug or Plastic",
    )

    product_ids = fields.Many2many(
        comodel_name="product.product",
        string="Product",
        help="Select specific products",
    )

    mo_status = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("progress", "In Progress"),
            ("to_close", "To Close"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ],
        string="MO Status",
    )

    workcenter_ids = fields.Many2many(
        comodel_name="mrp.workcenter",
        string="Work Center",
        help="Select work centers for scrap report",
    )

    # =====================
    # Default Get (Auto-select first report)
    # =====================
    @api.model
    def default_get(self, fields_list):
        res = super(MrpDailyReportWizard, self).default_get(fields_list)
        if "report_id" not in res:
            report = self.env["jasper.report"].search(
                [("model_id", "=", self._name)], limit=1
            )
            if report:
                res["report_id"] = report.id
        return res

    # =====================
    # Action Method
    # =====================
    def action_print_report(self):
        self.ensure_one()

        if self.date_from and self.date_to and self.date_from > self.date_to:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "แจ้งเตือน",
                    "message": "วันที่เริ่มต้นต้องไม่มากกว่าวันที่สิ้นสุด",
                    "type": "warning",
                    "sticky": False,
                },
            }

        if not self.report_id:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "แจ้งเตือน",
                    "message": "กรุณาเลือกรายงานก่อนทำการพิมพ์",
                    "type": "warning",
                    "sticky": False,
                },
            }

        def csv_or_none(ids):
            return ",".join(map(str, ids)) if ids else None

        if not self.mo_status:
            mo_status = "draft, confirmed, progress, to_close, done"
        else:
            mo_status = self.mo_status or ""

        if not self.workcenter_ids:
            workcenter_ids_sql = self.env["mrp.workcenter"].search([]).ids
        else:
            workcenter_ids_sql = self.workcenter_ids.ids

        if not self.product_ids:
            product_ids_sql = self.env["product.product"].search([]).ids
        else:
            product_ids_sql = self.product_ids.ids

        params = {
            "date_from": (
                fields.Date.to_string(self.date_from) if self.date_from else None
            ),
            "date_to": fields.Date.to_string(self.date_to) if self.date_to else None,
            "factory_tag_ids_sql": csv_or_none(self.factory_tag_ids.ids),
            "product_ids_sql": csv_or_none(product_ids_sql),
            "mo_status": mo_status,
            "workcenter_ids_sql": csv_or_none(workcenter_ids_sql),
            "printed_by": self.env.user.partner_id.name or self.env.user.name,
        }

        return self.report_id.run_report(docids=[self.id], data=params)
