from odoo import models, fields
import re


class SaleAnalysisMarketRegionXlsx(models.AbstractModel):
    _name = "report.sale_analysis_report.sale_analysis_market_region_xlsx"
    _inherit = "report.report_xlsx.abstract"

    def generate_xlsx_report(self, workbook, data, docs):
        wizard = docs[0]
        lines = wizard.line_ids

        if not lines:
            return

        scope_label = dict(wizard._fields["market_scope"].selection).get(
            wizard.market_scope, ""
        )
        report_title = f"Sales Report by Zone - {scope_label}"

        sheet = workbook.add_worksheet("Market Region Report")
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
        header_label_format = workbook.add_format(
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
        header_value_format = workbook.add_format(
            {
                "font_name": report_font,
                "font_size": 16,
                "bg_color": "#FFFFFF",
                "align": "left",
                "valign": "vcenter",
                "border": 1,
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
        cell_center_format = workbook.add_format(
            {
                "font_name": report_font,
                "font_size": 16,
                "align": "center",
                "valign": "vcenter",
                "border": 1,
            }
        )
        cell_left_format = workbook.add_format(
            {
                "font_name": report_font,
                "font_size": 16,
                "align": "left",
                "valign": "vcenter",
                "border": 1,
            }
        )
        money_format = workbook.add_format(
            {
                "font_name": report_font,
                "font_size": 16,
                "num_format": "#,##0.00",
                "align": "right",
                "valign": "vcenter",
                "border": 1,
            }
        )
        qty_format = workbook.add_format(
            {
                "font_name": report_font,
                "font_size": 16,
                "num_format": "#,##0.00",
                "align": "right",
                "valign": "vcenter",
                "border": 1,
            }
        )
        rate_format = workbook.add_format(
            {
                "font_name": report_font,
                "font_size": 16,
                "num_format": "#,##0.0000",
                "align": "right",
                "valign": "vcenter",
                "border": 1,
            }
        )

        # Alternating Row Formats
        cell_center_alt = workbook.add_format(
            {
                "font_name": report_font,
                "font_size": 16,
                "align": "center",
                "valign": "vcenter",
                "border": 1,
                "bg_color": "#F2F2F2",
            }
        )
        cell_left_alt = workbook.add_format(
            {
                "font_name": report_font,
                "font_size": 16,
                "align": "left",
                "valign": "vcenter",
                "border": 1,
                "bg_color": "#F2F2F2",
            }
        )
        money_alt = workbook.add_format(
            {
                "font_name": report_font,
                "font_size": 16,
                "num_format": "#,##0.00",
                "align": "right",
                "valign": "vcenter",
                "border": 1,
                "bg_color": "#F2F2F2",
            }
        )
        qty_alt = workbook.add_format(
            {
                "font_name": report_font,
                "font_size": 16,
                "num_format": "#,##0.00",
                "align": "right",
                "valign": "vcenter",
                "border": 1,
                "bg_color": "#F2F2F2",
            }
        )
        rate_alt = workbook.add_format(
            {
                "font_name": report_font,
                "font_size": 16,
                "num_format": "#,##0.0000",
                "align": "right",
                "valign": "vcenter",
                "border": 1,
                "bg_color": "#F2F2F2",
            }
        )
        summary_label_format = workbook.add_format(
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
        summary_value_format = workbook.add_format(
            {
                "bold": True,
                "font_name": report_font,
                "font_size": 16,
                "num_format": "#,##0.00",
                "bg_color": "#D9D9D9",
                "align": "right",
                "valign": "vcenter",
                "border": 2,
            }
        )

        # === Report Title ===
        sheet.merge_range("A1:H1", report_title, title_format)
        sheet.set_row(0, 35)

        # === Header Info ===
        row = 2
        sheet.write(row, 0, "Company Name", header_label_format)
        sheet.merge_range(row, 1, row, 3, wizard.env.company.name, header_value_format)
        sheet.write(row, 4, "Start Date", header_label_format)
        date_from_str = (
            wizard.date_from.strftime("%d/%m/%Y") if wizard.date_from else ""
        )
        sheet.merge_range(row, 5, row, 7, date_from_str, header_value_format)
        sheet.set_row(row, 25)
        row += 1

        sheet.write(row, 0, "Printed Date", header_label_format)
        date_today_str = fields.Date.today().strftime("%d/%m/%Y")
        sheet.merge_range(row, 1, row, 3, date_today_str, header_value_format)
        sheet.write(row, 4, "End Date", header_label_format)
        date_to_str = wizard.date_to.strftime("%d/%m/%Y") if wizard.date_to else ""
        sheet.merge_range(row, 5, row, 7, date_to_str, header_value_format)
        sheet.set_row(row, 25)

        # === Table Header ===
        row_header = 6
        sheet.set_row(row_header, 35)
        headers = [
            "SO No.",
            "Customer",
            "Product",
            "Quantity",
            "Currency",
            "Exchange Rate",
            "Amount (Foreign)",
            "Amount (THB)",
        ]

        for col, header in enumerate(headers):
            sheet.write(row_header, col, header, table_header_format)

        # === Table Data ===
        row_detail = row_header + 1
        total_foreign = 0
        total_thb = 0

        for idx, line in enumerate(lines):
            is_alt = idx % 2 == 1
            fmt_center = cell_center_alt if is_alt else cell_center_format
            fmt_left = cell_left_alt if is_alt else cell_left_format
            fmt_money = money_alt if is_alt else money_format
            fmt_qty = qty_alt if is_alt else qty_format
            fmt_rate = rate_alt if is_alt else rate_format

            amount_f = line.amount_foreign or 0.0
            amount_t = line.amount_thb or 0.0
            qty = line.product_uom_qty or 0.0

            sheet.write(row_detail, 0, line.sale_order_name or "", fmt_center)
            sheet.write(row_detail, 1, line.customer_name or "", fmt_left)
            sheet.write(row_detail, 2, line.product_name or "", fmt_left)
            sheet.write(row_detail, 3, qty, fmt_qty)
            sheet.write(row_detail, 4, line.currency_name or "", fmt_center)
            sheet.write(row_detail, 5, line.exchange_rate or 1.0, fmt_rate)
            sheet.write(row_detail, 6, amount_f, fmt_money)
            sheet.write(row_detail, 7, amount_t, fmt_money)

            total_foreign += amount_f
            total_thb += amount_t
            sheet.set_row(row_detail, 25)
            row_detail += 1

        # === Summary Row ===
        sheet.merge_range(row_detail, 0, row_detail, 5, "Total", summary_label_format)
        sheet.write(row_detail, 6, total_foreign, summary_value_format)
        sheet.write(row_detail, 7, total_thb, summary_value_format)
        sheet.set_row(row_detail, 30)

        sheet.set_column("A:A", 20)
        sheet.set_column("B:B", 30)
        sheet.set_column("C:C", 30)
        sheet.set_column("D:D", 12)
        sheet.set_column("E:E", 10)
        sheet.set_column("F:F", 15)
        sheet.set_column("G:G", 18)
        sheet.set_column("H:H", 18)
        sheet.freeze_panes(7, 0)
