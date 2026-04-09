# -*- coding: utf-8 -*-
from odoo import models, fields, api
from dateutil.relativedelta import relativedelta
from datetime import datetime, time


class DeliveryRouteReport(models.TransientModel):
    _name = "delivery.route.report"
    _description = "Delivery Route Report "

    name = fields.Char(
        string="Name",
        compute="_compute_name",
        store=True,
        help="(365 custom) ชื่อของรายงานที่จะแสดงในหน้าจอ (คำนวณจากสายส่งและวันที่)",
    )
    route_id = fields.Many2one(
        comodel_name="delivery.route",
        string="Route (สายส่ง)",
        help="(365 custom) เลือกสายส่งที่ต้องการสร้างรายงาน (ตัวเลือกนี้จะกรองพื้นที่ย่อยที่เกี่ยวข้องในตัวเลือกถัดไป)",
    )
    subregion_ids = fields.Many2many(
        comodel_name="delivery.sub.region",
        string="Sub-Region (เขต)",
        domain="[('route_id', '=', route_id)]",
        help="(365 custom) เลือกพื้นที่ย่อยที่ต้องการให้แสดงในรายงาน (กรองจากสายส่งที่เลือกไว้)",
    )
    date_from = fields.Date(
        string="Date From (วันที่เริ่มต้น)",
        help="(365 custom) วันที่เริ่มต้นของช่วงข้อมูลที่จะแสดงในรายงาน",
    )
    date_to = fields.Date(
        string="Date To (วันที่สิ้นสุด)",
        help="(365 custom) วันที่สิ้นสุดของช่วงข้อมูลที่จะแสดงในรายงาน",
    )
    report_id = fields.Many2one(
        comodel_name="jasper.report",
        string="Report (รายงาน)",
        domain="[('model_id', '=', 'delivery.route.report')]",
        help="(365 custom) เลือกเทมเพลตรายงานที่จะใช้ในการสร้างรายงาน (จะถูกค้นหาและกำหนดค่าโดยอัตโนมัติเมื่อเลือกสายส่ง)",
    )
    line_ids = fields.One2many(
        comodel_name="delivery.route.report.line",
        inverse_name="report_id",
        string="Report Lines",
    )

    @api.model
    def default_get(self, fields_list):
        res = super(DeliveryRouteReport, self).default_get(fields_list)
        if "date_from" in fields_list and not res.get("date_from"):
            res["date_from"] = fields.Date.today()

        if "date_to" in fields_list and not res.get("date_to"):
            res["date_to"] = fields.Date.today()

        if "report_id" in fields_list and not res.get("report_id"):
            report_domain = [("model_id", "=", "delivery.route.report")]
            found_report = self.env["jasper.report"].search(
                report_domain, order="id", limit=1
            )
            if found_report:
                res["report_id"] = found_report.id

        return res

    def _get_date_domain(self, field_prefix=""):
        """
        แปลง date_to ให้เป็นวันถัดไป แล้วใช้เครื่องหมาย <
        เพื่อให้ครอบคลุมเวลา 23:59:59 ของวันสิ้นสุด
        """
        self.ensure_one()

        # แปลง Date object ให้เป็น DateTime ที่เวลา 00:00:00
        dt_from = datetime.combine(self.date_from, time.min)
        dt_to = datetime.combine(self.date_to, time.min) + relativedelta(days=1)

        complete_name = f"{field_prefix}"

        return [
            (complete_name, ">=", dt_from),
            (complete_name, "<", dt_to),
        ]

    def _show_warning(self, title, message):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": message,
                "type": "warning",
                "sticky": False,
            },
        }

    @api.onchange("route_id")
    def _onchange_route_id(self):
        """
        TH: (onchange) ทำงานเมื่อมีการเปลี่ยนแปลง route_id (สายส่ง) หากมีการเลือกสายส่ง, จะทำการเลือก "All Sub-Regions" เป็น True, เติม subregion_ids ทั้งหมดที่อยู่ในสายส่งนั้น,
            กำหนดวันที่เริ่มต้น/สิ้นสุด, และค้นหารายงาน Jasper ที่เกี่ยวข้องโดยอัตโนมัติ หากยกเลิกการเลือก, จะล้างค่า "All Sub-Regions" และ subregion_ids
        EN: (onchange) Triggered when the route_id (Route) changes. If a route is selected, it sets "All Sub-Regions" to True, populates subregion_ids with
            all sub-regions from that route, sets default dates, and finds the related Jasper report. If the route is cleared, it clears the "All Sub-Regions"
            flag and the subregion_ids.
        """
        self.subregion_ids = [(5, 0, 0)]

    @api.depends("route_id", "date_from", "date_to")
    def _compute_name(self):
        for record in self:
            if record.route_id and record.date_from and record.date_to:
                d_from = record.date_from.strftime("%d/%m/%Y")
                d_to = record.date_to.strftime("%d/%m/%Y")
                record.name = (
                    f"รายงานใบจัดสาย {record.route_id.name} ({d_from} - {d_to})"
                )
            else:
                record.name = "รายงานใบจัดสาย"

    def action_generate_lines(self):
        """ฟังก์ชันสำหรับดึงข้อมูล SO และ Delivery ตามเงื่อนไข"""

        if self.date_from and self.date_to and self.date_from > self.date_to:
            return self._show_warning(
                "วันที่ไม่ถูกต้อง",
                "วันที่เริ่มต้นต้องไม่มากกว่าวันที่สิ้นสุด กรุณาตรวจสอบและแก้ไขวันที่ให้ถูกต้อง.",
            )

        self.line_ids = [(5, 0, 0)]
        domain = [
            ("state", "=", "done"),  # ต้องดำเนินการเสร็จสิ้นแล้วถึงจะมี date_done
            ("picking_type_code", "=", "outgoing"),  # เป็นใบส่งสินค้าขาออก
            ("sale_id", "!=", False),  # ต้องเชื่อมโยงกับ Sale Order
            ("sale_id.state", "in", ["sale", "done"]),  # สถานะ SO ต้องเป็น Sale Order
            (
                "sale_id.partner_id.subregion_id",
                "in",
                self.subregion_ids.ids,
            ),
        ]

        domain += self._get_date_domain(field_prefix="date_done")
        pickings = self.env["stock.picking"].search(domain)

        line_values = []
        for picking in pickings:
            line_values.append(
                (
                    0,
                    0,
                    {
                        "sale_id": picking.sale_id.id,
                        "picking_id": picking.id,
                    },
                )
            )

        self.line_ids = line_values

        return {
            "name": f"รายการจัดส่ง: {self.route_id.name}",
            "type": "ir.actions.act_window",
            "res_model": "delivery.route.report.line",
            "view_mode": "list",
            "view_id": self.env.ref(
                "delivery_route_report.view_delivery_route_report_line_list"
            ).id,
            "domain": [("report_id", "=", self.id)],
            "context": {
                "default_report_id": self.id,
                "active_report_id": self.id,
            },
            "target": "current",
        }

    def action_print_pdf(self):
        """
        TH: ทำงานเมื่อผู้ใช้กดยืนยัน (ปุ่ม action) ฟังก์ชันนี้จะรวบรวมข้อมูลที่ผู้ใช้เลือก (route, subregions, dates) และจัดรูปแบบให้อยู่ใน data dictionary จากนั้นเรียกใช้งาน
            run_report ของ Jasper Report ที่เลือกไว้เพื่อสร้างและส่งคืนผลลัพธ์รายงาน
        EN: The main confirmation action (e.g., "Print" button). This function gathers all user-selected data (route, subregions, dates),
            formats it into a data dictionary, and then executes the run_report method on the selected Jasper Report template to generate and return the report.
        """
        if not self.report_id:
            return self._show_warning(
                "รายงานไม่ถูกต้อง",
                "ไม่มีรายงาน ที่กำหนดไว้ กรุณาตรวจสอบการตั้งค่า.",
            )

        route_id = str(self.route_id.id) if self.route_id else None
        subregion_ids = (
            ",".join(map(str, self.subregion_ids.ids)) if self.subregion_ids else None
        )
        date_from = self.date_from.strftime("%Y-%m-%d") if self.date_from else None
        date_to = self.date_to.strftime("%Y-%m-%d") if self.date_to else None

        data = {
            "route_id": route_id,
            "subregion_ids": subregion_ids,
            "date_from": date_from,
            "date_to": date_to,
        }

        return self.report_id.run_report(docids=[self.ids[0]], data=data)

    def print_selected_lines(self, selected_line_ids):
        """ฟังก์ชันพิมพ์ที่จะถูกเรียกจากหน้า List View"""
        selected_ids_str = ",".join(map(str, selected_line_ids))

        route_id = str(self.route_id.id) if self.route_id else None
        subregion_ids = (
            ",".join(map(str, self.subregion_ids.ids)) if self.subregion_ids else None
        )
        date_from = self.date_from.strftime("%Y-%m-%d") if self.date_from else None
        date_to = self.date_to.strftime("%Y-%m-%d") if self.date_to else None

        data = {
            "route_id": route_id,
            "subregion_ids": subregion_ids,
            "date_from": date_from,
            "date_to": date_to,
            "selected_line_ids": selected_ids_str,
        }
        return self.report_id.run_report(docids=[self.id], data=data)
