from odoo import models


class AccountCommissionManagementXlsx(models.AbstractModel):
    _name = "report.account_commission_management.report_commission_excel"
    _inherit = "report.report_xlsx.abstract"
    _description = "Excel Report for Account Commission Management"

    def generate_xlsx_report(self, workbook, data, wizards):
        # สร้าง List ชื่อเดือนภาษาไทยสำหรับนำไปเทียบ
        thai_months = [
            "",
            "มกราคม",
            "กุมภาพันธ์",
            "มีนาคม",
            "เมษายน",
            "พฤษภาคม",
            "มิถุนายน",
            "กรกฎาคม",
            "สิงหาคม",
            "กันยายน",
            "ตุลาคม",
            "พฤศจิกายน",
            "ธันวาคม",
        ]

        for wizard in wizards:
            sheet = workbook.add_worksheet("รายงานค่าคอมมิชชั่น")

            # ==========================================
            # การตั้งค่ารูปแบบตัวอักษร (Angsana New)
            # ==========================================

            # รูปแบบชื่อบริษัทและหัวข้อหลัก (ขนาด 20, ตัวหนา, ไม่มีกรอบ)
            title_format = workbook.add_format(
                {
                    "font_name": "Angsana New",
                    "font_size": 20,
                    "bold": True,
                    "align": "center",
                    "valign": "vcenter",
                }
            )

            # รูปแบบหัวตาราง (ขนาด 18, ตัวหนา, มีพื้นหลังและกรอบ)
            header_format = workbook.add_format(
                {
                    "font_name": "Angsana New",
                    "font_size": 18,
                    "bold": True,
                    "align": "center",
                    "valign": "vcenter",
                    "border": 1,
                    "bg_color": "#D3D3D3",
                }
            )

            # รูปแบบข้อความทั่วไป (ขนาด 16)
            text_format = workbook.add_format(
                {
                    "font_name": "Angsana New",
                    "font_size": 16,
                    "align": "left",
                    "valign": "vcenter",
                    "border": 1,
                }
            )

            # รูปแบบวันที่ (ขนาด 16)
            date_format = workbook.add_format(
                {
                    "font_name": "Angsana New",
                    "font_size": 16,
                    "align": "center",
                    "valign": "vcenter",
                    "border": 1,
                    "num_format": "dd/mm/yyyy",
                }
            )

            # รูปแบบจำนวนเงิน (ขนาด 16)
            number_format = workbook.add_format(
                {
                    "font_name": "Angsana New",
                    "font_size": 16,
                    "align": "right",
                    "valign": "vcenter",
                    "border": 1,
                    "num_format": "#,##0.00",
                }
            )

            # ==========================================
            # การตั้งค่าความกว้างคอลัมน์ (A ถึง J)
            # ==========================================
            sheet.set_column("A:A", 25)  # พนักงานขาย
            sheet.set_column("B:B", 15)  # รหัสลูกค้า
            sheet.set_column("C:C", 35)  # ลูกค้า
            sheet.set_column("D:D", 15)  # วันที่ใบแจ้งหนี้
            sheet.set_column("E:E", 20)  # เลขที่ใบแจ้งหนี้
            sheet.set_column("F:F", 20)  # เลขที่ใบลดหนี้
            sheet.set_column("G:J", 20)  # ยอดเงินต่างๆ

            # ==========================================
            # เขียน Row 1 - 3 (Merge Columns A ถึง J (0-9))
            # ==========================================
            # Row 1: บริษัท
            sheet.merge_range(0, 0, 0, 9, "บริษัท โกลด์ มิ้นท์ โปรดักส์ จำกัด", title_format)

            # Row 2: ทะเบียนบิลกรุงเทพฯ
            sheet.merge_range(1, 0, 1, 9, "ทะเบียนบิลกรุงเทพฯ", title_format)

            # Row 3: ประจำเดือน (คำนวณเดือนและพ.ศ.)
            month_year_text = "ประจำเดือน "
            if wizard.date_from:
                month_idx = wizard.date_from.month
                thai_month_str = thai_months[month_idx]
                thai_year_str = str(wizard.date_from.year + 543)
                month_year_text += f"{thai_month_str} {thai_year_str}"

            sheet.merge_range(2, 0, 2, 9, month_year_text, title_format)

            # ==========================================
            # เขียน Row 4: หัวตาราง (Headers) เริ่มที่แถว index = 3
            # ==========================================
            headers = [
                "พนักงานขาย",
                "รหัสลูกค้า",
                "ลูกค้า",
                "วันที่ใบแจ้งหนี้",
                "เลขที่ใบแจ้งหนี้",
                "เลขที่ใบลดหนี้",
                "ยอดรวมใบแจ้งหนี้",
                "ยอดรวมใบลดหนี้",
                "ยอดรวมการชำระเงิน",
                "ยอดรวมค่าคอมมิชชั่น",
            ]

            for col_num, header in enumerate(headers):
                sheet.write(3, col_num, header, header_format)

            # ==========================================
            # เขียน Row 5 เป็นต้นไป: ข้อมูลจาก Line IDs (เริ่มแถว index = 4)
            # ==========================================
            row = 4
            for line in wizard.line_ids:
                # Text
                sheet.write(
                    row,
                    0,
                    line.salesperson_id.name if line.salesperson_id else "",
                    text_format,
                )
                sheet.write(row, 1, line.customer_code or "", text_format)
                sheet.write(row, 2, line.customer_name or "", text_format)

                # Date
                if line.invoice_date:
                    sheet.write_datetime(row, 3, line.invoice_date, date_format)
                else:
                    sheet.write(row, 3, "", text_format)

                # Text
                sheet.write(row, 4, line.invoice_name or "", text_format)
                sheet.write(row, 5, line.credit_note_name or "", text_format)

                # Number
                sheet.write_number(
                    row, 6, line.amount_invoice_total or 0.0, number_format
                )
                sheet.write_number(
                    row, 7, line.amount_credit_note_total or 0.0, number_format
                )
                sheet.write_number(
                    row, 8, line.amount_payment_total or 0.0, number_format
                )
                sheet.write_number(row, 9, line.amount_commission or 0.0, number_format)

                row += 1
