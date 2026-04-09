import io
import xlsxwriter


class AccountCustomerPaymentCollectionXlsx:
    def generate_excel(self, rows, date_from, date_to):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})

        self._write_sheet(workbook, rows, date_from, date_to)

        workbook.close()
        output.seek(0)
        return output.read()

    def _write_sheet(self, workbook, rows, date_from, date_to):
        date_from_str = date_from.strftime("%d/%m/%Y") if date_from else ""
        date_to_str = date_to.strftime("%d/%m/%Y") if date_to else ""

        sheet_name = (
            f"Customer Payment {date_from_str}-{date_to_str}"
            if date_from and date_to
            else "Customer Payment"
        )
        worksheet = workbook.add_worksheet(sheet_name[:31])

        formats = self._get_formats(workbook)

        columns = [
            (0, "ลูกค้า", "partner_name", formats["cell"]),
            (1, "ที่อยู่", "partner_address", formats["cell"]),
            (2, "รหัสลูกค้า", "partner_code", formats["cell"]),
            (3, "เลขที่บิล", "invoice_no", formats["cell"]),
            (4, "ไม่แวะไม่อยู่", "not_visit_flag", formats["cell"]),
            (5, "ส่วนลด", "discount_amount", formats["amount"]),
            (6, "หักบัญชี", "offset_amount", formats["amount"]),
            (7, "เงินสด", "cash_amount", formats["amount"]),
            (8, "เช็ค", "cheque_amount", formats["amount"]),
            (9, "เงินโอน", "transfer_amount", formats["amount"]),
            (10, "วางบิล", "billing_amount", formats["amount"]),
            (11, "วันที่โอนเช็ค", "cheque_transfer_date", formats["date"]),
        ]
        last_col = len(columns) - 1

        # --- Write Headers ---
        header_row = 4
        worksheet.set_row(0, 40)
        worksheet.merge_range(
            0, 0, 0, last_col, "รายงานการขายประจำวัน", formats["title"]
        )
        worksheet.merge_range(
            1,
            0,
            1,
            last_col,
            f"วันที่เริ่มต้น : {date_from_str}    วันที่สิ้นสุด : {date_to_str}",
            formats["sub_title"],
        )
        worksheet.merge_range(2, 0, 2, last_col, "ลงชื่อ :", formats["sub_title"])

        for col, title, _, _ in columns:
            worksheet.write(header_row, col, title, formats["header"])
            worksheet.set_column(col, col, 25)

        worksheet.set_row(header_row, 26)
        worksheet.freeze_panes(header_row + 1, 0)

        # --- Write Data ---
        row_no = header_row + 1
        for rec in rows:
            worksheet.set_row(row_no, 26)
            for col, _, field_name, fmt in columns:
                value = rec.get(field_name)
                if value is None:
                    worksheet.write_blank(row_no, col, None, fmt)
                else:
                    worksheet.write(row_no, col, value, fmt)
            row_no += 1

    def _get_formats(self, workbook):
        font_name = "Angsana New"
        return {
            "title": workbook.add_format(
                {
                    "bold": True,
                    "font_size": 18,
                    "font_name": font_name,
                    "align": "center",
                    "valign": "vcenter",
                    "bg_color": "#BFBFBF",
                    "pattern": 1,
                }
            ),
            "sub_title": workbook.add_format(
                {
                    "font_size": 14,
                    "font_name": font_name,
                    "align": "center",
                    "valign": "vcenter",
                }
            ),
            "header": workbook.add_format(
                {
                    "bold": True,
                    "font_size": 14,
                    "font_name": font_name,
                    "border": 1,
                    "valign": "vcenter",
                    "align": "center",
                }
            ),
            "cell": workbook.add_format(
                {
                    "border": 1,
                    "text_wrap": True,
                    "font_name": font_name,
                    "valign": "vcenter",
                    "font_size": 14,
                }
            ),
            "date": workbook.add_format(
                {
                    "border": 1,
                    "font_size": 14,
                    "font_name": font_name,
                    "valign": "vcenter",
                    "num_format": "dd/mm/yyyy",
                }
            ),
            "amount": workbook.add_format(
                {
                    "border": 1,
                    "font_size": 14,
                    "font_name": font_name,
                    "valign": "vcenter",
                    "num_format": "#,##0.00",
                }
            ),
        }
