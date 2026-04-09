# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError

class DeliveryRouteReport(models.TransientModel):
    _name = "delivery.route.report"
    _description = "Delivery Route Report "

    route_id = fields.Many2one(
        comodel_name="delivery.route",
        string="Route",
        help="(365 custom) Select the main region (delivery route) for the report.",
    )
    subregion_ids = fields.Many2many(
        comodel_name="delivery.sub.region",
        string="Sub-Region",
        help="(365 custom) Select the sub-regions to include in the report (filtered by the chosen Route).",
    )
    include_all_subregions = fields.Boolean(
        string="All Sub-Regions",
        default=False,
        help="(365 custom) Select this option to include all available sub-regions from the chosen Route.",
    )
    date_from = fields.Date(
        string="Date From",
        help="(365 custom) The start date for the report's data range.",
    )
    date_to = fields.Date(
        string="Date To",
        help="(365 custom) The end date for the report's data range.",
    )
    report_id = fields.Many2one(
        comodel_name="jasper.report",
        string="Report",
        help="(365 custom) Select the Jasper Report template to be used for this summary.",
    )

    def _set_default_dates(self):
        """
        TH: (Internal) กำหนดค่าเริ่มต้นของวันที่ date_from (เป็นวันปัจจุบัน) และ date_to (เป็นวันปัจจุบัน) หากยังไม่มีการกำหนดค่า 
        EN: (Internal) Sets the default dates for date_from (to the current day) and date_to (to the current day) if they are not already set.
        """
        if not self.date_from and not self.date_to:
            today = fields.Date.today()
            self.date_from = today
            self.date_to = today
    
    def _find_and_set_report(self):
        """
        TH: (Internal) ค้นหาและกำหนดค่า report_id (รายงาน Jasper) โดยอัตโนมัติ โดยค้นหาจาก jasper.report ที่มี model_id ตรงกับโมเดลปัจจุบัน (delivery.route.report) 
            หาก report_id ยังว่างอยู่
        EN: (Internal) Automatically finds and sets the report_id by searching for a jasper.report with a model_id matching the current model (delivery.route.report),
            if report_id is not already set.
        """
        if not self.report_id:
            report_domain = [("model_id", "=", "delivery.route.report")]
            found_report = self.env["jasper.report"].search(
                report_domain, 
                order="id", 
                limit=1
            )
            self.report_id = found_report.id if found_report else False

    @api.onchange("route_id")
    def _onchange_route_id(self):
        """
        TH: (onchange) ทำงานเมื่อมีการเปลี่ยนแปลง route_id (สายส่ง) หากมีการเลือกสายส่ง, จะทำการเลือก "All Sub-Regions" เป็น True, เติม subregion_ids ทั้งหมดที่อยู่ในสายส่งนั้น, 
            กำหนดวันที่เริ่มต้น/สิ้นสุด, และค้นหารายงาน Jasper ที่เกี่ยวข้องโดยอัตโนมัติ หากยกเลิกการเลือก, จะล้างค่า "All Sub-Regions" และ subregion_ids
        EN: (onchange) Triggered when the route_id (Route) changes. If a route is selected, it sets "All Sub-Regions" to True, populates subregion_ids with 
            all sub-regions from that route, sets default dates, and finds the related Jasper report. If the route is cleared, it clears the "All Sub-Regions" 
            flag and the subregion_ids.
        """
        if self.route_id:
            self.include_all_subregions = True
            self.subregion_ids = [(6, 0, self.route_id.subregion_ids.ids)]
            self._set_default_dates()
            self._find_and_set_report()
        else:
            self.include_all_subregions = False
            self.subregion_ids = [(5, 0, 0)]
    
    @api.onchange("include_all_subregions")
    def _onchange_include_all_subregions(self):
        """
        TH: (onchange) ทำงานเมื่อมีการเปลี่ยนแปลงค่า include_all_subregions (All Sub-Regions) หากเลือก True, จะทำการเลือก subregion_ids ทั้งหมดที่อยู่ใน route_id ที่เลือกไว้ 
            หากเลือก False, จะล้างค่า subregion_ids ทั้งหมด 
        EN: (onchange) Triggered when the include_all_subregions (All Sub-Regions) checkbox value changes. If checked (True), it populates subregion_ids with 
            all sub-regions from the selected route_id. If unchecked (False), it clears all subregion_ids.
        """
        if self.route_id:
            total_count = len(self.route_id.subregion_ids)
            if self.include_all_subregions:
                if len(self.subregion_ids) != total_count:
                    self.subregion_ids = [(6, 0, self.route_id.subregion_ids.ids)]
            else:
                if len(self.subregion_ids) == total_count:
                    self.subregion_ids = [(5, 0, 0)]

    @api.onchange("subregion_ids")
    def _onchange_subregion_ids(self):
        """
        TH: (onchange) ทำงานเมื่อมีการเปลี่ยนแปลง subregion_ids (พื้นที่ย่อย) ใช้สำหรับซิงค์สถานะของ checkbox include_all_subregions หากจำนวน subregion_ids 
            ที่เลือกเท่ากับจำนวนพื้นที่ย่อยทั้งหมดในสายส่ง, include_all_subregions จะเป็น True, มิฉะนั้นจะเป็น False 
        EN: (onchange) Triggered when the subregion_ids (Sub-Region) selection changes.This method syncs the state of the include_all_subregions checkbox.
            If the count of selected sub-regions matches the total count of sub-regions in the route, it sets include_all_subregions to True; otherwise, 
            it sets it to False.
        """
        if self.route_id:
            total_count = len(self.route_id.subregion_ids)
            selected_count = len(self.subregion_ids)

            if selected_count == total_count:
                self.include_all_subregions = True
            else:
                self.include_all_subregions = False
        
    @api.constrains("date_from", "date_to")
    def _check_date_range_constrains(self):
        """
        TH: (constrains) ตรวจสอบความถูกต้องของข้อมูล (constraint) ป้องกันไม่ให้ผู้ใช้บันทึกข้อมูลหาก date_from (วันที่เริ่มต้น) มีค่ามากกว่า date_to (วันที่สิ้นสุด) 
        EN: (constrains) A data constraint that validates the date range. It prevents saving if date_from is later than date_to and raises a UserError.
        """
        for record in self:
            if record.date_from and record.date_to and record.date_from > record.date_to:
                raise UserError("วันที่เริ่มต้น (Date From) ต้องมาก่อน หรือวันเดียวกับ วันที่สิ้นสุด (Date To)")

    def action_confirm(self):
        """
        TH: ทำงานเมื่อผู้ใช้กดยืนยัน (ปุ่ม action) ฟังก์ชันนี้จะรวบรวมข้อมูลที่ผู้ใช้เลือก (route, subregions, dates) และจัดรูปแบบให้อยู่ใน data dictionary จากนั้นเรียกใช้งาน 
            run_report ของ Jasper Report ที่เลือกไว้เพื่อสร้างและส่งคืนผลลัพธ์รายงาน
        EN: The main confirmation action (e.g., "Print" button). This function gathers all user-selected data (route, subregions, dates), 
            formats it into a data dictionary, and then executes the run_report method on the selected Jasper Report template to generate and return the report.
        """
        route_id = str(self.route_id.id) if self.route_id else None
        subregion_ids = ",".join(map(str, self.subregion_ids.ids)) if self.subregion_ids else None
        date_from = self.date_from.strftime("%Y-%m-%d") if self.date_from else None
        date_to = self.date_to.strftime("%Y-%m-%d") if self.date_to else None

        data = {
            "route_id": route_id,
            "subregion_ids": subregion_ids,
            "date_from": date_from,
            "date_to": date_to,
        }
        
        report_jasper = self.report_id
        if not report_jasper:
            raise UserError("ไม่มีรายงาน Jasper ที่กำหนดไว้สำหรับรายงานนี้ กรุณาตรวจสอบการตั้งค่า.")
        report_result = report_jasper.run_report(docids=[self.ids[0]], data=data)
        
        return report_result