# -*- coding: utf-8 -*-
import io
import re
from odoo import models, fields, _
from odoo.tools.misc import xlsxwriter


class AccountPaymentBillingReportExcel(models.AbstractModel):
    _name = "report.account_payment_billing_excel"
    _description = "Payment Billing Excel Report"

    def generate_xlsx_report(self, wizard):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})

        # --- 1. Formats ---
        font_name = "Angsana New"
        font_size = 16

        # Helper เพื่อสร้าง Border รอบตาราง
        border_style = 1  # 1 = Thin border

        # Format: ทั่วไป (ไม่มีขอบ) - ใช้สำหรับ Title ด้านบน
        f_text_plain = workbook.add_format(
            {
                "font_name": font_name,
                "font_size": font_size,
                "align": "left",
                "valign": "vcenter",
            }
        )

        # Format: หัวตาราง (Header) - มีขอบครบ
        f_header = workbook.add_format(
            {
                "font_name": font_name,
                "font_size": font_size,
                "bold": True,
                "align": "center",
                "valign": "vcenter",
                "border": border_style,  # ใส่ขอบทุกด้าน
                "bg_color": "#EEEEEE",  # (Optional) ใส่สีพื้นหลังอ่อนๆ ให้ดูสวยงาม
            }
        )

        # Format: ข้อมูลปกติในตาราง - มีขอบครบ
        f_normal_border = workbook.add_format(
            {
                "font_name": font_name,
                "font_size": font_size,
                "align": "left",
                "valign": "vcenter",
                "border": border_style,  # ใส่ขอบทุกด้าน
            }
        )

        # Format: จำนวนเงิน - มีขอบครบ
        f_amount_border = workbook.add_format(
            {
                "font_name": font_name,
                "font_size": font_size,
                "num_format": "#,##0.00",
                "align": "right",
                "valign": "vcenter",
                "border": border_style,
            }
        )

        # Format: รวม (ตัวหนา) - มีขอบครบ
        f_amount_bold_border = workbook.add_format(
            {
                "font_name": font_name,
                "font_size": font_size,
                "bold": True,
                "num_format": "#,##0.00",
                "align": "right",
                "valign": "vcenter",
                "border": border_style,
            }
        )

        # Format ส่วนหัวกระดาษ (ไม่มีขอบ)
        f_date_right = workbook.add_format(
            {
                "font_name": font_name,
                "font_size": font_size,
                "bold": True,
                "align": "right",
                "valign": "vcenter",
            }
        )
        f_title = workbook.add_format(
            {
                "font_name": font_name,
                "font_size": 20,
                "bold": True,
                "align": "center",
                "valign": "vcenter",
            }
        )
        f_subregion_header = workbook.add_format(
            {
                "font_name": font_name,
                "font_size": font_size,
                "bold": True,
                "align": "left",
                "valign": "vcenter",
            }
        )

        # --- 2. จัดกลุ่มข้อมูล (Group by Subregion Only) ---
        # 1. จัดเรียงข้อมูลตาม Subregion ก่อน
        all_lines = wizard.result_line_ids.sorted(
            key=lambda l: (l.subregion_name or "", l.invoice_date)
        )

        # 2. แยกตาม Subregion (เพื่อสร้าง Sheet)
        lines_by_sub = {}
        for line in all_lines:
            # ใช้ subregion_name เป็น Key หลัก (ซึ่งมีค่า "Route - Subregion" อยู่แล้ว)
            sub_key = line.subregion_name or "Unknown"
            if sub_key not in lines_by_sub:
                lines_by_sub[sub_key] = []
            lines_by_sub[sub_key].append(line)

        # วันที่พิมพ์
        today = fields.Date.today()
        buddhist_year = today.year + 543
        date_str = today.strftime(f"%d/%m/{buddhist_year}")

        # --- 3. วนลูปสร้าง Sheet ตาม Subregion ---
        for subregion_name, lines in lines_by_sub.items():
            # ตั้งชื่อ Sheet (ตัด Subregion ให้สั้นพอดี 31 ตัวอักษร และลบอักขระพิเศษ)
            # ถ้าชื่อยาวเกินไป อาจจะตัดแค่ส่วนท้ายที่เป็นชื่อ Subregion จริงๆ มาแสดง
            safe_sheet_name = re.sub(r'[\[\]:*?\/\\\'"]', "", subregion_name)[:31]
            worksheet = workbook.add_worksheet(safe_sheet_name)

            # ตั้งค่าความกว้าง Column
            worksheet.set_column("A:A", 8)  # ลำดับ
            worksheet.set_column("B:B", 15)  # รหัสลูกค้า
            worksheet.set_column("C:C", 35)  # ชื่อลูกค้า
            worksheet.set_column("D:D", 20)  # เลขที่บิล
            worksheet.set_column("E:E", 15)  # จำนวนเงิน
            worksheet.set_column("F:F", 15)  # รวม
            worksheet.set_column("G:G", 20)  # สถานะ

            row = 0

            # --- ส่วนหัวกระดาษ (ไม่มีเส้นขอบ) ---
            # 1. Header หลัก: ใบสรุปเก็บเงิน
            worksheet.merge_range(row, 0, row, 6, "ใบสรุปเก็บเงิน", f_title)
            row += 1

            # 2. Sub-Header: สาย... และ วันที่...
            worksheet.merge_range(
                row, 0, row, 3, f"สาย {subregion_name}", f_subregion_header
            )
            worksheet.merge_range(row, 4, row, 6, f"วันที่ {date_str}", f_date_right)
            row += 1

            # --- ส่วนตารางข้อมูล (มีเส้นขอบ) ---
            # 3. Table Header
            headers = [
                "ลำดับ",
                "รหัสลูกค้า",
                "ชื่อลูกค้า",
                "เลขที่บิล",
                "จำนวนเงิน",
                "รวม",
                "สถานะ",
            ]
            for col_idx, header in enumerate(headers):
                worksheet.write(row, col_idx, header, f_header)
            row += 1

            # 4. Data Rows
            for line in lines:
                # ช่องลำดับ (A) เว้นว่างไว้
                worksheet.write(row, 0, "", f_normal_border)

                worksheet.write(row, 1, line.partner_code, f_normal_border)
                worksheet.write(row, 2, line.partner_name, f_normal_border)
                worksheet.write(row, 3, line.invoice_name, f_normal_border)
                worksheet.write(row, 4, line.amount_total, f_amount_border)
                worksheet.write(row, 5, line.amount_total, f_amount_bold_border)
                worksheet.write(row, 6, line.invoice_summary, f_normal_border)
                row += 1

        workbook.close()
        return output.getvalue()
