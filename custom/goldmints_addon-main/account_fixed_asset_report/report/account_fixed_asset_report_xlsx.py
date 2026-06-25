import io
import xlsxwriter
from datetime import datetime


class AccountFixedAssetReportXlsx:
    def generate_excel(self, rows):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})

        self._write_sheet(workbook, rows)

        workbook.close()
        output.seek(0)
        return output.read()

    def _write_sheet(self, workbook, rows):

        sheet_name = f"Fixed Asset Report"

        worksheet = workbook.add_worksheet(sheet_name[:31])

        formats = self._get_formats(workbook)

        columns = [
            (0, "Asset Model", "asset_model", formats["cell"]),
            (1, "Asset Name", "asset_name", formats["cell"]),
            (2, "Acquisition Date", "acquisition_date", formats["date"]),
            (3, "Disposal/Close Date", "disposal_date", formats["date"]),
            (4, "Original Value", "original_value", formats["amount"]),
            (5, "Book Value", "book_value", formats["amount"]),
            (6, "Duration", "duration", formats["cell"]),
            (7, "Invoice No.", "invoice_name", formats["cell"]),
            (8, "Status", "detailed_status", formats["cell"]),
        ]

        last_col = len(columns) - 1
        # --- Write Headers ---
        header_row = 3
        worksheet.set_row(0, 40)
        worksheet.merge_range(0, 0, 0, last_col, "Fixed Asset Report", formats["title"])
        # เขียน header
        col_widths = {}
        for col, title, _, _ in columns:
            worksheet.write(header_row, col, title, formats["header"])
            # worksheet.set_column(col, col, 25)
            col_widths[col] = len(title)

        worksheet.set_row(header_row, 26)
        worksheet.freeze_panes(header_row + 1, 0)

        # --- Write Data ---
        row_no = header_row + 1
        for rec in rows:
            worksheet.set_row(row_no, 26)
            for col, _, field_name, fmt in columns:
                value = rec.get(field_name) or ""
                text = str(value)
                worksheet.write(row_no, col, value, fmt)
                col_widths[col] = max(col_widths.get(col, 0), len(text))
            row_no += 1
        for col, width in col_widths.items():
            worksheet.set_column(col, col, width + 2)

    def _get_formats(self, workbook):
        font_name = "Angsana New"
        return {
            "title": workbook.add_format(
                {
                    "bold": True,
                    "font_size": 20,
                    "font_name": font_name,
                    "align": "center",
                    "valign": "vcenter",
                    "bg_color": "#BFBFBF",
                    "pattern": 1,
                }
            ),
            "sub_title": workbook.add_format(
                {
                    "font_size": 16,
                    "font_name": font_name,
                    "align": "center",
                    "valign": "vcenter",
                }
            ),
            "header": workbook.add_format(
                {
                    "bold": True,
                    "font_size": 16,
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
                    "font_size": 16,
                }
            ),
            "date": workbook.add_format(
                {
                    "border": 1,
                    "font_size": 16,
                    "font_name": font_name,
                    "valign": "vcenter",
                    "num_format": "dd/mm/yyyy",
                }
            ),
            "amount": workbook.add_format(
                {
                    "border": 1,
                    "font_size": 16,
                    "font_name": font_name,
                    "valign": "vcenter",
                    "num_format": "#,##0.00",
                }
            ),
        }


class AccountAssetTransactionXlsx:
    def generate_excel(self, asset_data):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        self._write_sheet(workbook, asset_data)
        workbook.close()
        output.seek(0)
        return output.read()

    def _write_sheet(self, workbook, asset_data):
        worksheet = workbook.add_worksheet("Fixed Asset Transactions")

        worksheet.set_column("A:A", 24)  # Column A
        worksheet.set_column("B:B", 18)  # Column B
        worksheet.set_column("C:C", 73)  # Column C
        worksheet.set_column("D:D", 24)  # Column D
        worksheet.set_column("E:E", 15)  # Column E
        worksheet.set_column("F:F", 12)  # Column F
        worksheet.set_column("G:G", 27)  # Column G
        worksheet.set_column("H:H", 13)  # Column H
        worksheet.set_column("I:I", 15)  # Column I

        # กำหนด Formats ตาม Font Angsana New ขนาด 16 เป็นอย่างน้อย
        base_style = {"font_name": "Angsana New", "font_size": 16}
        header_style = workbook.add_format({**base_style, "bold": True})
        date_style = workbook.add_format({**base_style, "num_format": "dd/mm/yyyy"})
        amount_style = workbook.add_format({**base_style, "num_format": "#,##0.00"})
        normal_style = workbook.add_format(base_style)

        # สไตล์สำหรับ Header (หนา + เส้นล่าง)
        header_bottom_style = workbook.add_format(
            {**base_style, "bold": True, "bottom": 1}
        )
        # สไตล์สำหรับข้อมูลทั่วไป (เส้นล่าง)
        normal_bottom_style = workbook.add_format({**base_style, "bottom": 1})
        # สไตล์สำหรับวันที่/ตัวเลข (เส้นล่าง)
        amount_bottom_style = workbook.add_format(
            {**base_style, "bottom": 1, "num_format": "#,##0.00"}
        )

        # A1 & I1: Header ข้อมูลปัจจุบัน
        now = datetime.now()
        worksheet.write("A1", "Fixed asset transactions", header_style)
        worksheet.write("I1", f"Date: {now.strftime('%d/%m/%Y')}", normal_style)

        # A2 & I2: ข้อมูลบริษัทและเวลา
        worksheet.write("A2", "GOLD MINTS PRODUCTS CO., LTD.", header_style)
        worksheet.write("I2", f"Time: {now.strftime('%H:%M:%S')}", normal_style)

        row = 3
        for asset in asset_data:
            # Row 3 & 4: ข้อมูลหลักของ Asset
            # worksheet.write(row, 0, "Fixed asset", header_style)  # A3
            # row += 1

            headers_4 = [
                "Fixed asset group",
                "Fixed asset number",
                "Name",
                "Book",
                "Book type",
                "Status",
                "Location",
                "Acquisition",
                "Net book value",
            ]
            for col, text in enumerate(headers_4):
                # worksheet.write(row, col, text, header_style)
                worksheet.write(row, col, text, header_bottom_style)
            row += 1

            # ข้อมูล Row 5 (ดึงจาก account.asset)
            worksheet.write(row, 0, asset.get("group", ""), normal_style)
            worksheet.write(row, 1, asset.get("number", ""), normal_style)
            worksheet.write(row, 2, asset.get("name", ""), normal_style)
            worksheet.write(row, 3, asset.get("book", ""), normal_style)
            worksheet.write(row, 4, asset.get("book_type", ""), normal_style)
            worksheet.write(row, 5, asset.get("status", ""), normal_style)
            worksheet.write(row, 6, asset.get("location", ""), normal_style)
            worksheet.write(row, 7, asset.get("acquisition", ""), amount_style)
            worksheet.write(row, 8, asset.get("net_book_value", 0), amount_style)
            row += 2  # เว้นบรรทัดก่อนขึ้น Transaction

            # Row 6: ข้อมูล Transactions (ดึงจาก account.move)
            headers_6 = [
                "",
                "Transaction date",
                "Voucher",
                "Description",
                "Transaction type",
                "Amount",
                "Amount in transaction currency",
                "Currency",
            ]
            for col, text in enumerate(headers_6):
                if text:
                    # worksheet.write(row, col, text, header_style)
                    worksheet.write(row, col, text, header_bottom_style)
            row += 1

            worksheet.write(row, 1, asset.get("acquisition_date", ""), date_style)
            worksheet.write(row, 5, asset.get("acquisition", 0), amount_style)
            worksheet.write(row, 6, asset.get("acquisition", 0), amount_style)
            worksheet.write(row, 7, asset.get("currency", ""), normal_style)
            row += 1

            for line in asset.get("transactions", []):
                worksheet.write(row, 1, line.get("date", ""), date_style)
                worksheet.write(row, 2, line.get("voucher", ""), normal_style)
                worksheet.write(row, 3, line.get("description", ""), normal_style)
                worksheet.write(row, 4, line.get("type", ""), normal_style)
                worksheet.write(row, 5, line.get("amount", 0), amount_style)
                worksheet.write(row, 6, line.get("amount_curr", 0), amount_style)
                worksheet.write(row, 7, line.get("currency", ""), normal_style)
                row += 1

            acquisition_val = asset.get("acquisition", 0)
            sum_transactions = sum(
                t.get("amount", 0) for t in asset.get("transactions", [])
            )
            total_net_value = acquisition_val + sum_transactions
            worksheet.write(row, 1, "Total", header_style)
            worksheet.write(row, 5, total_net_value, amount_style)
            row += 2
