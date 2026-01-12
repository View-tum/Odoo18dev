# -*- coding: utf-8 -*-
from odoo import models, _
from datetime import date, datetime, timedelta

class ExpiredProductsReportXlsx(models.AbstractModel):
    """
    ตัวสร้างไฟล์ Excel จริง ๆ
    """
    _name = "report.inventory_expired_products_report.expired_products_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "Expired Products XLSX Report"

    def generate_xlsx_report(self, workbook, data, wizard):

        def _to_excel_date(raw, date_fmt, sheet, row, col, text_fmt):
            """แปลงค่าจาก DB ให้กลายเป็น Excel date เหมือน Jasper (+7 ชั่วโมง)"""
            if not raw:
                sheet.write(row, col, "", text_fmt)
                return

            # แปลงเป็น datetime ก่อน
            if isinstance(raw, datetime):
                dt = raw
            elif isinstance(raw, date):
                dt = datetime.combine(raw, datetime.min.time())
            else:
                s = str(raw)
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
                    try:
                        dt = datetime.strptime(s, fmt)
                        break
                    except Exception:
                        dt = None
                if not dt:
                    # เขียนเป็น text ถ้า parse ไม่ได้
                    sheet.write(row, col, s, text_fmt)
                    return

            # ✅ ทำให้เหมือน Jasper: +7 ชั่วโมง (Asia/Bangkok)
            dt = dt + timedelta(hours=7)
            sheet.write(row, col, dt, date_fmt)

        # wizard คือ expired.products.report ที่กดปุ่ม
        wizard = self.env["expired.products.report"].browse(
            data.get("wizard_id")
        )

        # ใช้ query เดียวกับ Excel เสมอ
        lines = wizard._get_xlsx_lines()

        sheet = workbook.add_worksheet(_("Expired Products")[:31])

        # ===== Formats - ปรับให้ดูเป็นทางการ =====
        
        # Title - สีน้ำเงินเข้ม เรียบๆ
        title_fmt = workbook.add_format({
            "bold": True,
            "font_size": 16,
            "font_name": "Tahoma",
            "align": "center",
            "valign": "vcenter",
            "bg_color": "#2C2C2C",  # เทาเข้มเกือบดำ
            "font_color": "white",
            "border": 1,
            "border_color": "#505050",
        })
        
        # Header - สีเทาอ่อน เรียบร้อย
        header_fmt = workbook.add_format({
            "bold": True,
            "font_size": 11,
            "font_name": "Tahoma",
            "align": "center",
            "valign": "vcenter",
            "bg_color": "#5A5A5A",  # เทากลาง
            "font_color": "white",
            "border": 1,
            "border_color": "#707070",
        })
        
        # Text - ข้อความทั่วไป
        text_fmt = workbook.add_format({
            "font_size": 10,
            "font_name": "Tahoma",
            "border": 1,
            "border_color": "#D0D0D0",
            "valign": "vcenter",
        })
        
        # Date format
        date_fmt = workbook.add_format({
            "font_size": 10,
            "font_name": "Tahoma",
            "border": 1,
            "border_color": "#D0D0D0",
            "align": "center",
            "valign": "vcenter",
            "num_format": "dd/mm/yyyy",
        })
        
        # Integer format (สำหรับ No.)
        int_fmt = workbook.add_format({
            "font_size": 10,
            "font_name": "Tahoma",
            "border": 1,
            "border_color": "#D0D0D0",
            "align": "center",
            "valign": "vcenter",
            "num_format": "0",
        })
        
        # Quantity format - มีพื้นหลังอ่อนๆ
        qty_fmt = workbook.add_format({
            "font_size": 10,
            "font_name": "Tahoma",
            "border": 1,
            "border_color": "#D0D0D0",
            "align": "right",
            "valign": "vcenter",
            "num_format": "#,##0.00",
            "bg_color": "#F2F2F2",  # สีเทาอ่อนมาก
        })
        
        # UoM format - ตรงกลาง
        uom_fmt = workbook.add_format({
            "font_size": 10,
            "font_name": "Tahoma",
            "border": 1,
            "border_color": "#D0D0D0",
            "align": "center",
            "valign": "vcenter",
        })

        # ===== Column width - ปรับให้กำลังดี =====
        sheet.set_column("A:A", 6)    # No.
        sheet.set_column("B:B", 16)   # Product Code
        sheet.set_column("C:C", 38)   # Product Name
        sheet.set_column("D:D", 26)   # Category
        sheet.set_column("E:E", 28)   # Location
        sheet.set_column("F:F", 20)   # Lot/Serial
        sheet.set_column("G:G", 14)   # Created On
        sheet.set_column("H:H", 14)   # Expiration Date
        sheet.set_column("I:I", 19)   # Manufacturing Date
        sheet.set_column("J:J", 12)   # Quantity
        sheet.set_column("K:K", 8)    # UoM

        # ตั้งความสูงของแถว Title และ Header
        sheet.set_row(0, 30)  # Title row
        sheet.set_row(2, 25)  # Header row

        row = 0

        # ===== Title =====
        sheet.merge_range(row, 0, row, 10, _("รายงานสินค้าหมดอายุ (Expired Products Report)"), title_fmt)
        row += 2

        # ===== Header =====
        headers = [
            _("No."),
            _("Product Code"),
            _("Product Name"),
            _("Category"),
            _("Location"),
            _("Lot/Serial"),
            _("Created On"),
            _("Expiration Date"),
            _("Manufacturing Date"),
            _("Quantity"),
            _("UoM"),
        ]
        for col, h in enumerate(headers):
            sheet.write(row, col, h, header_fmt)
        row += 1

        # ===== Data rows - สลับสีพื้นหลังเบาๆ =====
        # สร้าง alternate format สำหรับแถวคู่
        text_fmt_alt = workbook.add_format({
            "font_size": 10,
            "font_name": "Tahoma",
            "border": 1,
            "border_color": "#D0D0D0",
            "valign": "vcenter",
            "bg_color": "#F9F9F9",  # สีเทาอ่อนมากๆ
        })
        
        date_fmt_alt = workbook.add_format({
            "font_size": 10,
            "font_name": "Tahoma",
            "border": 1,
            "border_color": "#D0D0D0",
            "align": "center",
            "valign": "vcenter",
            "num_format": "dd/mm/yyyy",
            "bg_color": "#F9F9F9",
        })
        
        int_fmt_alt = workbook.add_format({
            "font_size": 10,
            "font_name": "Tahoma",
            "border": 1,
            "border_color": "#D0D0D0",
            "align": "center",
            "valign": "vcenter",
            "num_format": "0",
            "bg_color": "#F9F9F9",
        })
        
        qty_fmt_alt = workbook.add_format({
            "font_size": 10,
            "font_name": "Tahoma",
            "border": 1,
            "border_color": "#D0D0D0",
            "align": "right",
            "valign": "vcenter",
            "num_format": "#,##0.00",
            "bg_color": "#E8E8E8",
        })
        
        uom_fmt_alt = workbook.add_format({
            "font_size": 10,
            "font_name": "Tahoma",
            "border": 1,
            "border_color": "#D0D0D0",
            "align": "center",
            "valign": "vcenter",
            "bg_color": "#F9F9F9",
        })

        seq = 1
        for line in lines:
            # สลับสีแถว
            is_alt = (seq % 2 == 0)
            t_fmt = text_fmt_alt if is_alt else text_fmt
            d_fmt = date_fmt_alt if is_alt else date_fmt
            i_fmt = int_fmt_alt if is_alt else int_fmt
            q_fmt = qty_fmt_alt if is_alt else qty_fmt
            u_fmt = uom_fmt_alt if is_alt else uom_fmt
            
            sheet.write(row, 0, seq, i_fmt)
            sheet.write(row, 1, line.get("product_code") or "", t_fmt)
            sheet.write(row, 2, line.get("product_name") or "", t_fmt)
            sheet.write(row, 3, line.get("category_name") or "", t_fmt)
            sheet.write(row, 4, line.get("location_name") or "", t_fmt)
            sheet.write(row, 5, line.get("lot_name") or "", t_fmt)

            # G: Created On  (เหมือน Jasper: +7h)
            _to_excel_date(line.get("create_date"), d_fmt, sheet, row, 6, t_fmt)

            # H: Expiration Date (+7h)
            _to_excel_date(line.get("expiration_date"), d_fmt, sheet, row, 7, t_fmt)

            # I: Manufacturing Date (+7h)
            _to_excel_date(line.get("manufacturing_date"), d_fmt, sheet, row, 8, t_fmt)

            # J: Quantity
            sheet.write(row, 9, line.get("quantity") or 0.0, q_fmt)

            # K: UoM
            sheet.write(row,10, line.get("uom_name") or "", u_fmt)

            row += 1
            seq += 1
        
        # เพิ่ม Freeze Panes ที่แถว Header
        sheet.freeze_panes(3, 0)