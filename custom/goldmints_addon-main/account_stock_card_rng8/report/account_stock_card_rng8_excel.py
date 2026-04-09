# inventory_stock_card_rng8/report/inventory_stock_card_rng8_excel.py
import io
import xlsxwriter


class AccountStockCardRng8ExcelWriter:
    def __init__(self):
        self.font_name = "Angsana New"
        self.header_bg = "#EEEEEE"

    def _get_formats(self, wb):
        return {
            "title": wb.add_format(
                {
                    "bold": True,
                    "font_size": 18,
                    "font_name": self.font_name,
                    "align": "center",
                    "valign": "vcenter",
                }
            ),
            "date_info": wb.add_format(
                {
                    "bold": True,
                    "font_size": 16,
                    "font_name": self.font_name,
                    "align": "left",
                }
            ),
            "header_merged": wb.add_format(
                {
                    "bold": True,
                    "border": 1,
                    "align": "center",
                    "valign": "vcenter",
                    "bg_color": self.header_bg,
                    "font_name": self.font_name,
                    "font_size": 16,
                }
            ),
            "header_sub": wb.add_format(
                {
                    "bold": True,
                    "border": 1,
                    "align": "center",
                    "bg_color": self.header_bg,
                    "font_name": self.font_name,
                    "font_size": 14,
                }
            ),
            "text": wb.add_format(
                {
                    "border": 1,
                    "align": "left",
                    "font_name": self.font_name,
                    "font_size": 16,
                }
            ),
            "num": wb.add_format(
                {
                    "border": 1,
                    "align": "right",
                    "num_format": "#,##0.00",
                    "font_name": self.font_name,
                    "font_size": 16,
                }
            ),
            "num_bold": wb.add_format(
                {
                    "border": 1,
                    "align": "right",
                    "num_format": "#,##0.00",
                    "font_name": self.font_name,
                    "font_size": 16,
                    "bold": False,
                }
            ),
        }

    def generate(self, metadata, data_lines):
        bio = io.BytesIO()
        wb = xlsxwriter.Workbook(bio, {"in_memory": True})
        ws = wb.add_worksheet("Stock Card")

        fmt = self._get_formats(wb)

        ws.set_column(0, 0, 15)
        ws.set_column(1, 1, 20)
        ws.set_column(2, 2, 35)
        ws.set_column(3, 14, 12)
        ws.merge_range(0, 0, 0, 14, "ข้อมูลในการทำเอกสาร รง.8 ประจำเดือน", fmt["title"])
        date_range_str = (
            f"ข้อมูลวันที่ {metadata.get('date_from')} - {metadata.get('date_to')}"
        )
        ws.write(1, 0, date_range_str, fmt["date_info"])

        h_row = 3
        ws.merge_range(h_row, 0, h_row + 1, 0, "รหัสสินค้า", fmt["header_merged"])
        ws.merge_range(h_row, 1, h_row + 1, 1, "หมวดสินค้า", fmt["header_merged"])
        ws.merge_range(h_row, 2, h_row + 1, 2, "ชื่อสินค้า", fmt["header_merged"])

        ws.merge_range(h_row, 3, h_row, 5, "Beginning Balance", fmt["header_merged"])
        ws.merge_range(h_row, 6, h_row, 8, "Received", fmt["header_merged"])
        ws.merge_range(h_row, 9, h_row, 11, "Issued", fmt["header_merged"])
        ws.merge_range(h_row, 12, h_row, 14, "Balance", fmt["header_merged"])

        sub_h_row = 4
        sub_headers = [
            "Quantity",
            "Cost",
            "Amount",  # Beginning
            "Quantity",
            "Cost",
            "Amount",  # Received
            "Quantity",
            "Cost",
            "Amount",  # Issued
            "Quantity",
            "Unit Cost",
            "Cost Amount",  # Balance
        ]

        col_idx = 3
        for h in sub_headers:
            ws.write(sub_h_row, col_idx, h, fmt["header_sub"])
            col_idx += 1

        row = 5
        for line in data_lines:
            ws.write(row, 0, line.get("code") or "", fmt["text"])
            ws.write(row, 1, line.get("category") or "", fmt["text"])
            ws.write(row, 2, line.get("name") or "", fmt["text"])

            # Beginning
            ws.write(row, 3, line.get("open_qty", 0), fmt["num"])
            ws.write(row, 4, line.get("open_cost", 0), fmt["num"])
            ws.write(row, 5, line.get("open_val", 0), fmt["num"])

            # Received
            ws.write(row, 6, line.get("in_qty", 0), fmt["num"])
            ws.write(row, 7, line.get("in_cost", 0), fmt["num"])
            ws.write(row, 8, line.get("in_val", 0), fmt["num"])

            # Issued
            ws.write(row, 9, line.get("out_qty", 0), fmt["num"])
            ws.write(row, 10, line.get("out_cost", 0), fmt["num"])
            ws.write(row, 11, line.get("out_val", 0), fmt["num"])

            # Balance
            ws.write(row, 12, line.get("end_qty", 0), fmt["num"])
            ws.write(row, 13, line.get("end_cost", 0), fmt["num_bold"])
            ws.write(row, 14, line.get("end_val", 0), fmt["num"])

            row += 1

        wb.close()
        return bio.getvalue()
