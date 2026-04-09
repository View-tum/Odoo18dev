# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError

class InvoicePaymentReport(models.TransientModel):
    _name = "invoice.payment.report"
    _description = "Invoice Payment Report"

    salesperson_ids = fields.Many2many(
        comodel_name="res.users",
        string="Salespersons",
        domain=lambda self: self._get_salesperson_domain(),
        help="(365 custom) Select one or more salespersons to include in the report.",
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
    
    def _get_salesperson_domain(self):
        """
        TH: (Internal) สร้างและส่งคืนค่า Domain (เงื่อนไขการค้นหา) สำหรับฟิลด์ salesperson_ids เพื่อจำกัดให้สามารถเลือกได้เฉพาะผู้ใช้ที่อยู่ในกลุ่ม "Salesman",
            "Salesman All Leads", หรือ "Manager" เท่านั้น
        EN: (Internal) Builds and returns a search domain for the salesperson_ids field, restricting the selectable users to only those who are members of the "Salesman",
            "Salesman All Leads", or "Manager" security groups.
        """
        group_salesman = self.env.ref("sales_team.group_sale_salesman", raise_if_not_found=False)
        group_salesman_all = self.env.ref("sales_team.group_sale_salesman_all_leads", raise_if_not_found=False)
        group_manager = self.env.ref("sales_team.group_sale_manager", raise_if_not_found=False)

        group_ids = []
        if group_salesman:
            group_ids.append(group_salesman.id)
        if group_salesman_all:
            group_ids.append(group_salesman_all.id)
        if group_manager:
            group_ids.append(group_manager.id)
        return [
            ("groups_id", "in", group_ids)
        ]
    
    def _set_default_dates(self):
        """
        TH: (Internal) กำหนดค่าเริ่มต้นของวันที่ date_from (เป็นวันแรกของเดือนปัจจุบัน) และ date_to (เป็นวันปัจจุบัน) หากยังไม่มีการกำหนดค่า
        EN: (Internal) Sets the default dates for date_from (to the first day of the current month) and date_to (to the current day) if they are not already set.
        """
        if not self.date_from and not self.date_to:
            today = fields.Date.today()
            self.date_from = today.replace(day=1)
            self.date_to = today
    
    def _find_and_set_report(self):
        """
        TH: (Internal) ค้นหาและกำหนดค่า report_id (รายงาน Jasper) โดยอัตโนมัติ โดยค้นหาจาก jasper.report ที่มี model_id ตรงกับโมเดลปัจจุบัน (invoice.payment.report)
            หาก report_id ยังว่างอยู่
        EN: (Internal) Automatically finds and sets the report_id by searching for a jasper.report with a model_id matching the current model (invoice.payment.report),
                if report_id is not already set.
        """
        if not self.report_id:
            report_domain = [("model_id", "=", "invoice.payment.report")]
            found_report = self.env["jasper.report"].search(
                report_domain, 
                order="id", 
                limit=1
            )
            self.report_id = found_report.id if found_report else False
                
    @api.onchange("salesperson_ids")
    def _onchange_salesperson_ids(self):
        """
        TH: (onchange) ทำงานเมื่อมีการเปลี่ยนแปลง salesperson_ids (พนักงานขาย) หากมีการเลือกพนักงานขายอย่างน้อยหนึ่งคน, จะทำการกำหนดวันที่เริ่มต้น/สิ้นสุด 
            และค้นหารายงาน Jasper โดยอัตโนมัติ
        EN: (onchange) Triggered when the salesperson_ids field changes. If at least one salesperson is selected, it automatically sets 
            the default dates and finds the related Jasper report.
        """
        if self.salesperson_ids:
            self._set_default_dates()
            self._find_and_set_report()

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
        TH: ทำงานเมื่อผู้ใช้กดยืนยัน (ปุ่ม action) ฟังก์ชันนี้จะรวบรวมข้อมูลที่ผู้ใช้เลือก (salesperson IDs, dates) และจัดรูปแบบให้อยู่ใน data dictionary จากนั้นเรียกใช้งาน run_report
            ของ Jasper Report ที่เลือกไว้เพื่อสร้างและส่งคืนผลลัพธ์รายงาน
        EN: The main confirmation action (e.g., "Print" button). This function gathers all user-selected data (salesperson IDs, dates),
            formats it into a data dictionary, and then executes the run_report method on the selected Jasper Report template to generate and return the report.
        """
        salesperson_ids = ",".join(map(str, self.salesperson_ids.ids)) if self.salesperson_ids else None
        date_from = self.date_from.strftime("%Y-%m-%d") if self.date_from else None
        date_to = self.date_to.strftime("%Y-%m-%d") if self.date_to else None

        data = {
            "salesperson_ids": salesperson_ids,
            "date_from": date_from,
            "date_to": date_to,
        }
        
        report_jasper = self.report_id
        if not report_jasper:
            raise UserError("ไม่มีรายงาน Jasper ที่กำหนดไว้สำหรับรายงานนี้ กรุณาตรวจสอบการตั้งค่า.")
        report_result = report_jasper.run_report(docids=[self.ids[0]], data=data)
        
        return report_result