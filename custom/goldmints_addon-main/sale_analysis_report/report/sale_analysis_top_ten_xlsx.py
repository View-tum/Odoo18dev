from odoo import models, fields, api


class SaleAnalysisTopTenXlsx(models.AbstractModel):
    _name = "report.sale_analysis_report.sale_analysis_top_ten_xlsx"
    _inherit = "report.report_xlsx.abstract"

    def generate_xlsx_report(self, workbook, data, docs):
        wizard = docs[0]

        # Extract data
        top_qty_lines = wizard.line_ids.filtered(lambda l: l.rank_type == "qty")
        top_amount_lines = wizard.line_ids.filtered(lambda l: l.rank_type == "amount")

        report_font = "Angsana New"

        # === Formats ===
        title_format = workbook.add_format(
            {
                "bold": True,
                "font_size": 20,
                "font_name": report_font,
                "align": "center",
                "valign": "vcenter",
                "bg_color": "#D9D9D9",
                "border": 1,
            }
        )
        table_title_fmt = workbook.add_format(
            {
                "bold": True,
                "font_name": report_font,
                "font_size": 18,
                "align": "left",
                "bg_color": "#F2F2F2",
                "border": 1,
            }
        )
        header_fmt = workbook.add_format(
            {
                "bold": True,
                "font_name": report_font,
                "font_size": 16,
                "align": "center",
                "valign": "vcenter",
                "bg_color": "#D9D9D9",
                "border": 1,
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

        # === Create Single Sheet ===
        sheet = workbook.add_worksheet("Top 10 Analysis")
        sheet.set_column("A:A", 7)
        sheet.set_column("B:B", 50)
        sheet.set_column("C:C", 22)
        sheet.set_column("D:D", 22)

        # Global Header
        sheet.merge_range("A1:D1", "Top 10 Best Selling Products", title_format)
        sheet.set_row(0, 35)

        row = 2

        # --- Block 1: By Quantity ---
        sheet.merge_range(row, 0, row, 3, "Top 10 by Quantity", table_title_fmt)
        row += 1

        headers = ["Rank", "Product", "Quantity (Units)", "Sales Amount (THB)"]
        for col, head in enumerate(headers):
            sheet.write(row, col, head, header_fmt)
        row += 1

        for index, line in enumerate(top_qty_lines, 1):
            sheet.write(row, 0, index, cell_center)
            sheet.write(row, 1, line.product_name, cell_text)
            sheet.write(row, 2, line.product_uom_qty, cell_num)
            sheet.write(row, 3, line.amount_sale_total, cell_num)
            row += 1

        row += 2  # Gap

        # --- Block 2: By Revenue ---
        sheet.merge_range(row, 0, row, 3, "Top 10 by Sales Amount", table_title_fmt)
        row += 1

        for col, head in enumerate(headers):
            sheet.write(row, col, head, header_fmt)
        row += 1

        for index, line in enumerate(top_amount_lines, 1):
            sheet.write(row, 0, index, cell_center)
            sheet.write(row, 1, line.product_name, cell_text)
            sheet.write(row, 2, line.product_uom_qty, cell_num)
            sheet.write(row, 3, line.amount_sale_total, cell_num)
            row += 1
