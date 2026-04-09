from odoo import models, fields, api
import re


class SaleAnalysisProductXlsx(models.AbstractModel):
    _name = "report.sale_analysis_report.sale_analysis_product_xlsx"
    _inherit = "report.report_xlsx.abstract"

    def generate_xlsx_report(self, workbook, data, docs):
        wizard = docs[0]
        # Group by product name
        product_names = wizard.line_ids.mapped("product_name")

        if not product_names:
            return

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
        header_label = workbook.add_format(
            {
                "bold": True,
                "font_name": report_font,
                "font_size": 16,
                "bg_color": "#D9D9D9",
                "align": "left",
                "valign": "vcenter",
                "border": 1,
            }
        )
        header_val = workbook.add_format(
            {
                "font_name": report_font,
                "font_size": 16,
                "align": "left",
                "valign": "vcenter",
                "border": 1,
            }
        )

        # Section Header
        section_header_fmt = workbook.add_format(
            {
                "bold": True,
                "font_name": report_font,
                "font_size": 16,
                "align": "left",
                "valign": "vcenter",
                "bg_color": "#F2F2F2",
                "border": 1,
            }
        )
        section_val_fmt = workbook.add_format(
            {
                "bold": True,
                "font_name": report_font,
                "font_size": 16,
                "align": "left",
                "valign": "vcenter",
                "bg_color": "#F2F2F2",
                "border": 1,
                "text_wrap": True,
            }
        )

        table_header_format = workbook.add_format(
            {
                "bold": True,
                "font_name": report_font,
                "font_size": 16,
                "bg_color": "#D9D9D9",
                "align": "center",
                "valign": "vcenter",
                "border": 1,
                "text_wrap": True,
            }
        )

        cell_fmt = workbook.add_format(
            {
                "font_name": report_font,
                "font_size": 16,
                "border": 1,
                "align": "left",
                "valign": "vcenter",
            }
        )
        cell_center = workbook.add_format(
            {
                "font_name": report_font,
                "font_size": 16,
                "border": 1,
                "align": "center",
                "valign": "vcenter",
            }
        )
        money_fmt = workbook.add_format(
            {
                "font_name": report_font,
                "font_size": 16,
                "num_format": "#,##0.00_);(#,##0.00)",
                "border": 1,
                "align": "right",
                "valign": "vcenter",
            }
        )
        qty_fmt = workbook.add_format(
            {
                "font_name": report_font,
                "font_size": 16,
                "num_format": "#,##0.00_);(#,##0.00)",
                "border": 1,
                "align": "right",
                "valign": "vcenter",
            }
        )

        sum_label = workbook.add_format(
            {
                "bold": True,
                "font_name": report_font,
                "font_size": 16,
                "bg_color": "#D9D9D9",
                "align": "right",
                "valign": "vcenter",
                "border": 2,
            }
        )
        sum_val = workbook.add_format(
            {
                "bold": True,
                "font_name": report_font,
                "font_size": 16,
                "num_format": "#,##0.00_);(#,##0.00)",
                "bg_color": "#D9D9D9",
                "align": "right",
                "valign": "vcenter",
                "border": 2,
            }
        )

        # === Create Single Sheet ===
        sheet = workbook.add_worksheet("Sales Report")

        sheet.set_column("A:A", 30)  # Salesperson
        sheet.set_column("B:B", 30)  # Customer
        sheet.set_column("C:C", 22)  # SO
        sheet.set_column("D:D", 18)  # Qty
        sheet.set_column("E:E", 27)  # Amount & Category

        # === Global Header ===
        sheet.merge_range("A1:E1", "Sales Report by Product", title_format)
        sheet.set_row(0, 35)

        # Header Info
        row = 2
        sheet.write(row, 0, "Company Name", header_label)
        sheet.merge_range(row, 1, row, 2, wizard.env.company.name, header_val)
        sheet.write(row, 3, "Start Date", header_label)
        sheet.write(row, 4, wizard.date_from.strftime("%d/%m/%Y"), header_val)
        row += 1

        print_date = fields.Date.context_today(wizard).strftime("%d/%m/%Y")
        sheet.write(row, 0, "Printed Date", header_label)
        sheet.merge_range(row, 1, row, 2, print_date, header_val)
        sheet.write(row, 3, "End Date", header_label)
        sheet.write(row, 4, wizard.date_to.strftime("%d/%m/%Y"), header_val)

        # Start Data Loop
        row = 5

        for product_name in set(product_names):
            lines = wizard.line_ids.filtered(lambda l: l.product_name == product_name)
            if not lines:
                continue

            first_line = lines[0]
            category_name = first_line.product_category_name or ""

            # 1. Section Header (Product Info)
            sheet.write(row, 0, "Product", section_header_fmt)
            sheet.merge_range(row, 1, row, 2, product_name, section_val_fmt)
            sheet.write(row, 3, "Category", section_header_fmt)
            sheet.write(row, 4, category_name, section_val_fmt)
            row += 1

            # 2. Table Header
            sheet.write(row, 0, "Salesperson", table_header_format)
            sheet.write(row, 1, "Customer", table_header_format)
            sheet.write(row, 2, "SO No.", table_header_format)
            sheet.write(row, 3, "Quantity\n(Units)", table_header_format)
            sheet.write(row, 4, "Sales Amount\n(Untaxed)", table_header_format)
            sheet.set_row(row, 35)
            row += 1

            # 3. Data Lines
            total_qty = 0
            total_amt = 0

            for line in lines:
                sheet.write(row, 0, line.salesperson_id.name or "", cell_center)
                sheet.write(row, 1, line.customer_name or "", cell_fmt)
                sheet.write(row, 2, line.sale_order_name or "", cell_fmt)

                qty = line.product_uom_qty or 0.0
                amt = line.amount_sale_total or 0.0

                sheet.write(row, 3, qty, qty_fmt)
                sheet.write(row, 4, amt, money_fmt)

                total_qty += qty
                total_amt += amt
                row += 1

            # 4. Summary
            sheet.merge_range(row, 0, row, 2, "Total", sum_label)
            sheet.write(row, 3, total_qty, sum_val)
            sheet.write(row, 4, total_amt, sum_val)

            row += 2  # Gap
