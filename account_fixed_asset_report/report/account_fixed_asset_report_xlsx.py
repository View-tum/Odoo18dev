import io
import xlsxwriter


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
