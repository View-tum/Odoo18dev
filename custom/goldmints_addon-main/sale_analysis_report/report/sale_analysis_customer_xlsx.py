from odoo import models, fields, api
from datetime import datetime


class SaleAnalysisCustomerXlsx(models.AbstractModel):
    _name = "report.sale_analysis_report.sale_analysis_customer_xlsx"
    _inherit = "report.report_xlsx.abstract"

    def generate_xlsx_report(self, workbook, data, docs):
        wizard = docs[0]
        lines = wizard.line_ids

        # หา unique customers โดยยังคงลำดับเดิม (ถ้ามี) หรือ sort ตามชื่อ
        customer_names = sorted(list(set(lines.mapped("customer_name")) or []))

        if not customer_names:
            return

        report_font = "Angsana New"

        # === Define Formats ===
        # Title
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

        # Header Label (Company, Date labels)
        header_label = workbook.add_format(
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

        # Header Value
        header_val = workbook.add_format(
            {
                "font_name": report_font,
                "font_size": 16,
                "align": "left",
                "valign": "vcenter",
                "border": 1,
            }
        )

        # Customer Header (The row showing "Customer: XXX")
        cust_header_fmt = workbook.add_format(
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
        cust_val_fmt = workbook.add_format(
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

        # Table Header (Salesperson, SO No., etc)
        table_head = workbook.add_format(
            {
                "bold": True,
                "font_name": report_font,
                "font_size": 16,
                "bg_color": "#D9D9D9",
                "border": 1,
                "align": "center",
                "text_wrap": True,
                "valign": "vcenter",
            }
        )

        # Cell Formats
        cell_fmt = workbook.add_format(
            {"font_name": report_font, "font_size": 16, "border": 1, "align": "left"}
        )
        cell_center = workbook.add_format(
            {"font_name": report_font, "font_size": 16, "border": 1, "align": "center"}
        )
        money_fmt = workbook.add_format(
            {
                "font_name": report_font,
                "font_size": 16,
                "num_format": "#,##0.00_);(#,##0.00)",
                "border": 1,
                "align": "right",
            }
        )

        # Summary Formats
        sum_label = workbook.add_format(
            {
                "bold": True,
                "font_name": report_font,
                "font_size": 16,
                "bg_color": "#D9D9D9",
                "border": 1,
                "align": "right",
            }
        )
        sum_val = workbook.add_format(
            {
                "bold": True,
                "font_name": report_font,
                "font_size": 16,
                "num_format": "#,##0.00_);(#,##0.00)",
                "bg_color": "#D9D9D9",
                "border": 1,
                "align": "right",
            }
        )

        # === Create Single Sheet ===
        sheet = workbook.add_worksheet("Sales Report")

        # Set Column Widths
        sheet.set_column("A:A", 25)  # Salesperson
        sheet.set_column("B:D", 18)  # SO, INV, CN No.
        sheet.set_column("E:H", 18)  # Amounts

        # === Global Header ===
        # Row 1: Title
        sheet.merge_range("A1:H1", "Sales Report by Customer", title_format)
        sheet.set_row(0, 35)

        # Row 3: Company & Start Date
        # A3: "Company Name"
        sheet.write(2, 0, "Company Name", header_label)
        sheet.merge_range(2, 1, 2, 3, wizard.env.company.name, header_val)

        sheet.write(2, 4, "Start Date", header_label)
        sheet.merge_range(2, 5, 2, 7, wizard.date_from.strftime("%d/%m/%Y"), header_val)

        # Row 4: Printed Date & End Date
        print_date = fields.Date.context_today(wizard).strftime("%d/%m/%Y")
        sheet.write(3, 0, "Printed Date", header_label)
        sheet.merge_range(3, 1, 3, 3, print_date, header_val)

        sheet.write(3, 4, "End Date", header_label)
        sheet.merge_range(3, 5, 3, 7, wizard.date_to.strftime("%d/%m/%Y"), header_val)

        # Start Data Loop
        row = 5  # Start at Row 6 (Index 5)

        for customer_name in customer_names:
            cust_lines = lines.filtered(lambda l: l.customer_name == customer_name)
            if not cust_lines:
                continue

            # 1. Customer Name Header
            sheet.write(row, 0, "Customer", cust_header_fmt)
            sheet.merge_range(row, 1, row, 7, customer_name, cust_val_fmt)
            row += 1

            # 2. Table Headers
            headers = [
                "Salesperson",
                "SO No.",
                "INV No.",
                "CN No.",
                "Sales Amount",
                "Sales (INV)",
                "Refund",
                "Payment",
            ]
            for col, h in enumerate(headers):
                sheet.write(row, col, h, table_head)
            sheet.set_row(row, 30)
            row += 1

            # 3. Data Lines
            totals = [0.0] * 4  # Sale, Inv, Refund, Pay

            for line in cust_lines:
                sheet.write(row, 0, line.salesperson_id.name or "", cell_fmt)
                sheet.write(row, 1, line.sale_order_name or "", cell_center)
                sheet.write(row, 2, line.invoice_name or "", cell_center)
                sheet.write(row, 3, line.credit_note_name or "", cell_center)

                vals = [
                    line.amount_sale_total,
                    line.amount_invoice_total,
                    line.amount_credit_note_total,  # Refund
                    line.amount_payment_total,  # Payment
                ]

                for i, val in enumerate(vals):
                    sheet.write(row, 4 + i, val, money_fmt)
                    totals[i] += val

                row += 1

            sheet.merge_range(row, 0, row, 3, "Total", sum_label)
            for i, val in enumerate(totals):
                sheet.write(row, 4 + i, val, sum_val)

            row += 2
