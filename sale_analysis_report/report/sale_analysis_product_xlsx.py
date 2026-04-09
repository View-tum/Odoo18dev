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
                "font_color": "#000000",
                "bg_color": "#D9D9D9",
                "border": 1,
            }
        )
        header_label_format = workbook.add_format(
            {
                "bold": True,
                "font_name": report_font,
                "font_size": 16,
                "bg_color": "#D9D9D9",
                "font_color": "#000000",
                "border": 1,
                "align": "left",
                "valign": "vcenter",
            }
        )
        header_value_format = workbook.add_format(
            {
                "font_name": report_font,
                "font_size": 16,
                "bg_color": "#FFFFFF",
                "border": 1,
                "align": "left",
                "valign": "vcenter",
            }
        )
        table_header_format = workbook.add_format(
            {
                "bold": True,
                "font_name": report_font,
                "font_size": 16,
                "bg_color": "#D9D9D9",
                "font_color": "#000000",
                "border": 1,
                "align": "center",
                "valign": "vcenter",
                "text_wrap": True,
            }
        )
        cell_format = workbook.add_format(
            {
                "font_name": report_font,
                "font_size": 16,
                "border": 1,
                "align": "left",
                "valign": "vcenter",
            }
        )
        cell_center_format = workbook.add_format(
            {
                "font_name": report_font,
                "font_size": 16,
                "border": 1,
                "align": "center",
                "valign": "vcenter",
                "text_wrap": True,
            }
        )
        money_format = workbook.add_format(
            {
                "font_name": report_font,
                "font_size": 16,
                "num_format": "#,##0.00",
                "border": 1,
                "align": "right",
                "valign": "vcenter",
            }
        )
        qty_format = workbook.add_format(
            {
                "font_name": report_font,
                "font_size": 16,
                "num_format": "#,##0.00",
                "border": 1,
                "align": "right",
                "valign": "vcenter",
            }
        )
        cell_format_alt = workbook.add_format(
            {
                "font_name": report_font,
                "font_size": 16,
                "bg_color": "#F2F2F2",
                "border": 1,
                "align": "left",
                "valign": "vcenter",
            }
        )
        cell_center_format_alt = workbook.add_format(
            {
                "font_name": report_font,
                "font_size": 16,
                "bg_color": "#F2F2F2",
                "border": 1,
                "align": "center",
                "valign": "vcenter",
                "text_wrap": True,
            }
        )
        money_format_alt = workbook.add_format(
            {
                "font_name": report_font,
                "font_size": 16,
                "num_format": "#,##0.00",
                "bg_color": "#F2F2F2",
                "border": 1,
                "align": "right",
                "valign": "vcenter",
            }
        )
        qty_format_alt = workbook.add_format(
            {
                "font_name": report_font,
                "font_size": 16,
                "num_format": "#,##0.00",
                "bg_color": "#F2F2F2",
                "border": 1,
                "align": "right",
                "valign": "vcenter",
            }
        )
        summary_label_format = workbook.add_format(
            {
                "bold": True,
                "font_name": report_font,
                "font_size": 16,
                "bg_color": "#D9D9D9",
                "font_color": "#000000",
                "border": 2,
                "align": "right",
                "valign": "vcenter",
            }
        )
        summary_value_format = workbook.add_format(
            {
                "bold": True,
                "font_name": report_font,
                "font_size": 16,
                "num_format": "#,##0.00",
                "bg_color": "#D9D9D9",
                "font_color": "#000000",
                "border": 2,
                "align": "right",
                "valign": "vcenter",
            }
        )
        summary_qty_format = workbook.add_format(
            {
                "bold": True,
                "font_name": report_font,
                "font_size": 16,
                "num_format": "#,##0.00",
                "bg_color": "#D9D9D9",
                "font_color": "#000000",
                "border": 2,
                "align": "right",
                "valign": "vcenter",
            }
        )

        # Loop creating Sheet by product name
        for product_name in set(product_names):
            lines = wizard.line_ids.filtered(lambda l: l.product_name == product_name)

            first_line = lines[0]
            category_name = first_line.product_category_name or ""

            invalid_chars = r"[\[\]:*?/\\]"
            sheet_name = re.sub(invalid_chars, "_", product_name)[:31]
            sheet = workbook.add_worksheet(sheet_name)

            # === Report Title ===
            sheet.merge_range("A1:E1", "Sales Report by Product", title_format)
            sheet.set_row(0, 35)

            # === Header Info ===
            row = 2

            # Row 1
            sheet.write(row, 0, "Company Name", header_label_format)
            sheet.merge_range(
                row, 1, row, 2, wizard.env.company.name, header_value_format
            )
            sheet.write(row, 3, "Start Date", header_label_format)
            date_from_str = (
                wizard.date_from.strftime("%d/%m/%Y") if wizard.date_from else ""
            )
            sheet.write(row, 4, date_from_str, header_value_format)
            sheet.set_row(row, 25)
            row += 1

            # Row 2
            sheet.write(row, 0, "Product Category", header_label_format)
            sheet.merge_range(row, 1, row, 2, category_name, header_value_format)
            sheet.write(row, 3, "End Date", header_label_format)
            date_to_str = wizard.date_to.strftime("%d/%m/%Y") if wizard.date_to else ""
            sheet.write(row, 4, date_to_str, header_value_format)
            sheet.set_row(row, 25)
            row += 1

            # Row 3
            sheet.write(row, 0, "Product Name", header_label_format)
            sheet.merge_range(row, 1, row, 2, product_name, header_value_format)
            sheet.write(row, 3, "Printed Date", header_label_format)
            date_today_str = fields.Date.today().strftime("%d/%m/%Y")
            sheet.write(row, 4, date_today_str, header_value_format)
            sheet.set_row(row, 25)

            # === Table Header ===
            row_header_detail = 6
            sheet.set_row(row_header_detail, 35)
            sheet.write(row_header_detail, 0, "Salesperson", table_header_format)
            sheet.write(row_header_detail, 1, "Customer", table_header_format)
            sheet.write(row_header_detail, 2, "SO No.", table_header_format)
            sheet.write(row_header_detail, 3, "Quantity\n(Units)", table_header_format)
            sheet.write(
                row_header_detail, 4, "Sales Amount\n(Untaxed)", table_header_format
            )

            # === Table Details ===
            row_detail = row_header_detail + 1
            total_quantity = 0
            total_amount = 0

            for idx, line in enumerate(lines):
                is_alternate = idx % 2 == 1
                row_center_format = (
                    cell_center_format_alt if is_alternate else cell_center_format
                )
                row_cell_format = cell_format_alt if is_alternate else cell_format
                row_qty_format = qty_format_alt if is_alternate else qty_format
                row_money_format = money_format_alt if is_alternate else money_format

                sheet.write(
                    row_detail, 0, line.salesperson_id.name or "", row_center_format
                )
                sheet.write(row_detail, 1, line.customer_name or "", row_cell_format)
                sheet.write(row_detail, 2, line.sale_order_name or "", row_cell_format)

                qty = line.product_uom_qty or 0.0
                amt = line.amount_sale_total or 0.0

                sheet.write(row_detail, 3, qty, row_qty_format)
                sheet.write(row_detail, 4, amt, row_money_format)

                total_quantity += qty
                total_amount += amt

                sheet.set_row(row_detail, 25)
                row_detail += 1

            # === Summary ===
            sheet.merge_range(
                row_detail, 0, row_detail, 2, "Total", summary_label_format
            )
            sheet.write(row_detail, 3, total_quantity, summary_qty_format)
            sheet.write(row_detail, 4, total_amount, summary_value_format)
            sheet.set_row(row_detail, 30)

            sheet.set_column("A:A", 30)
            sheet.set_column("B:B", 30)
            sheet.set_column("C:C", 22)
            sheet.set_column("D:D", 18)
            sheet.set_column("E:E", 18)
            sheet.freeze_panes(7, 0)
