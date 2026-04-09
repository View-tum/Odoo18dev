from odoo import models, fields
import re


class SaleAnalysisSalemanXlsx(models.AbstractModel):
    _name = "report.sale_analysis_report.sale_analysis_saleman_xlsx"
    _inherit = "report.report_xlsx.abstract"

    def generate_xlsx_report(self, workbook, data, docs):
        """docs is recordset of sale.analysis.report (wizard)"""
        wizard = docs[0]
        wizard.ensure_one()

        salespersons = wizard.line_ids.mapped("salesperson_id")
        if not salespersons:
            return

        report_font = "Angsana New"

        # === Define Formats Once ===
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

        # Alternate Row Formats
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

        # Pre-calculate common strings
        date_from_str = (
            wizard.date_from.strftime("%d/%m/%Y") if wizard.date_from else ""
        )
        date_to_str = wizard.date_to.strftime("%d/%m/%Y") if wizard.date_to else ""
        date_today_str = fields.Date.today().strftime("%d/%m/%Y")
        company_name = wizard.env.company.name

        for salesperson in salespersons:
            # Filter lines for this salesperson
            person_lines = wizard.line_ids.filtered(
                lambda l: l.salesperson_id == salesperson
            )

            salesperson_name = salesperson.name or "Unknown"
            invalid_chars = r"[\[\]:*?/\\]"
            sheet_name = re.sub(invalid_chars, "_", salesperson_name)[:31]
            sheet = workbook.add_worksheet(sheet_name)

            # === Report Title ===
            sheet.merge_range("A1:I1", "Sales Report by Salesperson", title_format)
            sheet.set_row(0, 35)

            region_name = salesperson.salesregion_id.name or "-"

            # === Header Information Section ===
            row = 2
            sheet.write(row, 0, "Company Name", header_label_format)
            sheet.merge_range(row, 1, row, 3, company_name, header_value_format)
            sheet.write(row, 4, "Start Date", header_label_format)
            sheet.merge_range(row, 5, row, 8, date_from_str, header_value_format)
            sheet.set_row(row, 25)
            row += 1

            sheet.write(row, 0, "Sales Region", header_label_format)
            sheet.merge_range(row, 1, row, 3, region_name, header_value_format)
            sheet.write(row, 4, "End Date", header_label_format)
            sheet.merge_range(row, 5, row, 8, date_to_str, header_value_format)
            sheet.set_row(row, 25)
            row += 1

            sheet.write(row, 0, "Salesperson", header_label_format)
            sheet.merge_range(row, 1, row, 3, salesperson_name, header_value_format)
            sheet.write(row, 4, "Printed Date", header_label_format)
            sheet.merge_range(row, 5, row, 8, date_today_str, header_value_format)
            sheet.set_row(row, 25)

            # === Table Header ===
            row_header_detail = 6
            headers = [
                ("SO No.", 0),
                ("Customer", 1),
                ("Invoice No.", 2),
                ("Credit Note No.", 3),
                ("Sales Amount (Untaxed)", 4, 5),
                ("Payment\n(Collected)", 6),
                ("Refund Amount\n(Untaxed)", 7),
                ("Commission\n(Calculated)", 8),
            ]

            for h in headers:
                if len(h) == 3:  # Merge
                    sheet.merge_range(
                        row_header_detail,
                        h[1],
                        row_header_detail,
                        h[2],
                        h[0],
                        table_header_format,
                    )
                else:
                    sheet.merge_range(
                        row_header_detail,
                        h[1],
                        row_header_detail + 1,
                        h[1],
                        h[0],
                        table_header_format,
                    )

            sheet.write(row_header_detail + 1, 4, "SO", table_header_format)
            sheet.write(row_header_detail + 1, 5, "INV", table_header_format)
            sheet.set_row(row_header_detail, 25)
            sheet.set_row(row_header_detail + 1, 25)

            # === Table Details ===
            row_detail = row_header_detail + 2
            total_sale = 0
            total_invoice = 0
            total_credit = 0
            total_payment = 0
            total_commission = 0

            for idx, line in enumerate(person_lines):
                is_alternate = idx % 2 == 1
                row_cell_format = cell_format_alt if is_alternate else cell_format
                row_center_format = (
                    cell_center_format_alt if is_alternate else cell_center_format
                )
                row_money_format = money_format_alt if is_alternate else money_format

                so_name = line.sale_order_name or ""
                cust_name = line.customer_name or ""
                inv_name = line.invoice_name or ""
                cn_name = line.credit_note_name or ""

                amount_sale = line.amount_sale_total or 0.0
                amount_invoice = line.amount_invoice_total or 0.0
                amount_payment = line.amount_payment_total or 0.0
                amount_credit = line.amount_credit_note_total or 0.0
                amount_commission = line.amount_commission or 0.0

                sheet.write(row_detail, 0, so_name, row_center_format)
                sheet.write(row_detail, 1, cust_name, row_cell_format)
                sheet.write(row_detail, 2, inv_name, row_center_format)
                sheet.write(row_detail, 3, cn_name, row_center_format)

                sheet.write(row_detail, 4, amount_sale, row_money_format)
                sheet.write(row_detail, 5, amount_invoice, row_money_format)
                sheet.write(row_detail, 6, amount_payment, row_money_format)
                sheet.write(row_detail, 7, amount_credit, row_money_format)
                sheet.write(row_detail, 8, amount_commission, row_money_format)

                total_sale += amount_sale
                total_invoice += amount_invoice
                total_credit += amount_credit
                total_payment += amount_payment
                total_commission += amount_commission

                inv_lines = inv_name.count("\n") + 1 if inv_name else 1
                cn_lines = cn_name.count("\n") + 1 if cn_name else 1
                max_lines = max(inv_lines, cn_lines)
                height = max(25, max_lines * 20)

                sheet.set_row(row_detail, height)
                row_detail += 1

            # === Summary Row ===
            sheet.merge_range(
                row_detail, 0, row_detail, 3, "Total", summary_label_format
            )
            sheet.write(row_detail, 4, total_sale, summary_value_format)
            sheet.write(row_detail, 5, total_invoice, summary_value_format)
            sheet.write(row_detail, 6, total_payment, summary_value_format)
            sheet.write(row_detail, 7, total_credit, summary_value_format)
            sheet.write(row_detail, 8, total_commission, summary_value_format)
            sheet.set_row(row_detail, 30)

            # === Column Widths ===
            sheet.set_column("A:A", 22)
            sheet.set_column("B:B", 30)
            sheet.set_column("C:I", 18)  # Optimized set_column
            sheet.freeze_panes(8, 0)
