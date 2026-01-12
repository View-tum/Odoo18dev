from odoo import models, fields, api


class SaleAnalysisTopTenXlsx(models.AbstractModel):
    _name = "report.sale_analysis_report.sale_analysis_top_ten_xlsx"
    _inherit = "report.report_xlsx.abstract"

    def generate_xlsx_report(self, workbook, data, docs):
        wizard = docs[0]

        # Extract data from line_ids
        top_qty_lines = wizard.line_ids.filtered(lambda l: l.rank_type == "qty")
        top_amount_lines = wizard.line_ids.filtered(lambda l: l.rank_type == "amount")

        # Convert to list of dicts
        top_qty_data = [
            {
                "product_name": l.product_name,
                "quantity": l.product_uom_qty,
                "amount": l.amount_sale_total,
            }
            for l in top_qty_lines
        ]
        top_amount_data = [
            {
                "product_name": l.product_name,
                "quantity": l.product_uom_qty,
                "amount": l.amount_sale_total,
            }
            for l in top_amount_lines
        ]

        report_font = "Angsana New"

        header_format = workbook.add_format(
            {
                "bold": True,
                "font_name": report_font,
                "font_size": 18,
                "align": "center",
                "valign": "vcenter",
                "border": 1,
                "bg_color": "#D9D9D9",
            }
        )
        cell_text = workbook.add_format(
            {
                "font_name": report_font,
                "font_size": 16,
                "border": 1,
                "valign": "vcenter",
            }
        )

        cell_center = workbook.add_format(
            {
                "font_name": report_font,
                "font_size": 16,
                "border": 1,
                "valign": "vcenter",
                "align": "center",
            }
        )

        cell_num = workbook.add_format(
            {
                "font_name": report_font,
                "font_size": 16,
                "border": 1,
                "valign": "vcenter",
                "align": "right",
                "num_format": "#,##0.00",
            }
        )
        title_format = workbook.add_format(
            {"bold": True, "font_name": report_font, "font_size": 20, "align": "center"}
        )

        sheet_qty = workbook.add_worksheet("Top 10 Quantity")
        self._write_sheet(
            sheet_qty,
            top_qty_data,
            "Top 10 Best Selling Products (By Quantity)",
            title_format,
            header_format,
            cell_text,
            cell_num,
            cell_center,
        )

        sheet_amount = workbook.add_worksheet("Top 10 Revenue")
        self._write_sheet(
            sheet_amount,
            top_amount_data,
            "Top 10 Best Selling Products (By Sales Amount)",
            title_format,
            header_format,
            cell_text,
            cell_num,
            cell_center,
        )

    def _write_sheet(
        self, sheet, data, title, title_fmt, head_fmt, text_fmt, num_fmt, center_fmt
    ):
        sheet.merge_range("A1:D1", title, title_fmt)

        headers = ["Rank", "Product", "Quantity (Units)", "Sales Amount (THB)"]
        for col, head in enumerate(headers):
            sheet.write(2, col, head, head_fmt)

        sheet.set_column("A:A", 7)
        sheet.set_column("B:B", 50)
        sheet.set_column("C:C", 22)
        sheet.set_column("D:D", 22)

        row = 3
        for index, item in enumerate(data, 1):
            sheet.write(row, 0, index, center_fmt)
            sheet.write(row, 1, item["product_name"], text_fmt)
            sheet.write(row, 2, item["quantity"], num_fmt)
            sheet.write(row, 3, item["amount"], num_fmt)
            row += 1
