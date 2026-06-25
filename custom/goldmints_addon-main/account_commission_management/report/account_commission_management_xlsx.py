from odoo import models


class AccountCommissionManagementXlsx(models.AbstractModel):
    _name = "report.account_commission_management.report_commission_excel"
    _inherit = "report.report_xlsx.abstract"
    _description = "Excel Report for Account Commission Management"

    def generate_xlsx_report(self, workbook, data, wizards):
        # รายชื่อเดือนภาษาไทย
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

            # --- Formats ---
            title_format = workbook.add_format(
                {
                    "font_name": "Angsana New",
                    "font_size": 20,
                    "bold": True,
                    "align": "center",
                    "valign": "vcenter",
                }
            )
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
            text_format = workbook.add_format(
                {
                    "font_name": "Angsana New",
                    "font_size": 16,
                    "align": "left",
                    "valign": "vcenter",
                    "border": 1,
                }
            )
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

            # --- Column Widths (A to M) ---
            sheet.set_column("A:A", 18)  # Invoice Date
            sheet.set_column("B:D", 20)  # SO, Invoice, CN
            sheet.set_column("E:E", 15)  # Customer Code
            sheet.set_column("F:F", 35)  # Customer Name
            sheet.set_column("G:G", 25)  # Saleperson
            sheet.set_column("H:K", 20)  # Amounts
            sheet.set_column("L:L", 30)  # รวม
            sheet.set_column("M:M", 10)  # Count

            # --- Header Titles (Merge A to M / 0 to 12) ---
            sheet.merge_range(
                0, 0, 0, 12, "บริษัท โกลด์ มิ้นท์ โปรดักส์ จำกัด", title_format
            )
            sheet.merge_range(1, 0, 1, 12, "ทะเบียนบิลกรุงเทพฯ", title_format)

            month_year_text = "ประจำเดือน "
            if wizard.date_from:
                month_idx = wizard.date_from.month
                thai_month_str = thai_months[month_idx]
                thai_year_str = str(wizard.date_from.year + 543)
                month_year_text += f"{thai_month_str} {thai_year_str}"
            sheet.merge_range(2, 0, 2, 12, month_year_text, title_format)

            # --- Table Headers ---
            headers = [
                "วันที่ใบแจ้งหนี้",  # A (0)
                "ใบสั่งขาย",  # B (1)
                "เลขที่ใบแจ้งหนี้",  # C (2)
                "เลขที่ใบลดหนี้",  # D (3)
                "รหัสลูกค้า",  # E (4)
                "ลูกค้า",  # F (5)
                "พนักงานขาย",  # G (6)
                "ยอดรวมใบแจ้งหนี้",  # H (7)
                "ยอดรวมใบลดหนี้",  # I (8)
                "ยอดรวมการชำระเงิน",  # J (9)
                "ยอดรวมค่าคอมมิชชั่น",  # K (10)
                "รวม",  # L (11)
                "Count",  # M (12)
            ]
            for col_num, header in enumerate(headers):
                sheet.write(3, col_num, header, header_format)

            # --- Data Rows ---
            row = 4
            for line in wizard.line_ids:
                # A: Invoice Date
                if line.invoice_date:
                    sheet.write_datetime(row, 0, line.invoice_date, date_format)
                else:
                    sheet.write(row, 0, "", text_format)

                # B: Sale order, C: Invoice, D: Credit Note
                sheet.write(row, 1, line.sale_order_name or "", text_format)
                sheet.write(row, 2, line.invoice_name or "", text_format)
                sheet.write(row, 3, line.credit_note_name or "", text_format)

                # E: Customer Code, F: Customer Name, G: Saleperson
                sheet.write(row, 4, line.customer_code or "", text_format)
                sheet.write(row, 5, line.customer_name or "", text_format)
                sheet.write(
                    row,
                    6,
                    line.salesperson_id.name if line.salesperson_id else "",
                    text_format,
                )

                # H-K: Amounts
                sheet.write_number(
                    row, 7, line.amount_invoice_total or 0.0, number_format
                )
                sheet.write_number(
                    row, 8, line.amount_credit_note_total or 0.0, number_format
                )
                sheet.write_number(
                    row, 9, line.amount_payment_total or 0.0, number_format
                )
                sheet.write_number(
                    row, 10, line.amount_commission or 0.0, number_format
                )

                # L: รวม (Formula: E & G)
                # row_num คือลำดับแถวใน Excel (เริ่มจาก 1)
                row_num = row + 1
                formula_combined = f"=E{row_num}&G{row_num}"
                sheet.write_formula(row, 11, formula_combined, text_format)

                # M: Count (Formula: If current L = previous L then 0 else 1)
                # บรรทัดแรก (row 5) จะเทียบกับ Header (row 4) ซึ่งไม่ตรงกันอยู่แล้ว จะได้ค่า 1
                formula_count = f"=IF(L{row_num}=L{row_num-1},0,1)"
                sheet.write_formula(row, 12, formula_count, text_format)

                row += 1
