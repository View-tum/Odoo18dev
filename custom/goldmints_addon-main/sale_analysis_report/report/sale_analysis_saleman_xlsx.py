from odoo import models, fields
import re


class SaleAnalysisSalemanXlsx(models.AbstractModel):
    _name = "report.sale_analysis_report.sale_analysis_saleman_xlsx"
    _inherit = "report.report_xlsx.abstract"

    def generate_xlsx_report(self, workbook, data, docs):
        wizard = docs[0]
        wizard.ensure_one()

        # Group by Salesperson
        salespersons = wizard.line_ids.mapped("salesperson_id")
        if not salespersons:
            return

        report_font = "Angsana New"

        # === Define Formats ===
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

        # Section Header (Salesperson Name)
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

        # Set Column Widths (A-I)
        sheet.set_column("A:A", 22)  # SO
        sheet.set_column("B:B", 30)  # Customer
        sheet.set_column("C:I", 18)  # Amounts

        # === Global Header ===
        # ปรับ Title Merge ตามจำนวน Column ที่จะแสดง
        col_end = "I" if wizard.is_commission_confirmed else "H"
        sheet.merge_range(f"A1:{col_end}1", "Sales Report by Salesperson", title_format)
        sheet.set_row(0, 35)

        # Header Info
        row = 2
        sheet.write(row, 0, "Company Name", header_label)
        sheet.merge_range(row, 1, row, 3, wizard.env.company.name, header_val)
        sheet.write(row, 4, "Start Date", header_label)
        sheet.merge_range(
            row, 5, row, 7, wizard.date_from.strftime("%d/%m/%Y"), header_val
        )
        row += 1

        print_date = fields.Date.context_today(wizard).strftime("%d/%m/%Y")
        sheet.write(row, 0, "Printed Date", header_label)
        sheet.merge_range(row, 1, row, 3, print_date, header_val)
        sheet.write(row, 4, "End Date", header_label)
        sheet.merge_range(
            row, 5, row, 7, wizard.date_to.strftime("%d/%m/%Y"), header_val
        )

        # Start Data Loop
        row = 5

        for salesperson in salespersons:
            person_lines = wizard.line_ids.filtered(
                lambda l: l.salesperson_id == salesperson
            )
            if not person_lines:
                continue

            salesperson_name = salesperson.name or "Unknown"
            region_name = salesperson.salesregion_id.name or "-"

            # 1. Section Header (Salesperson info)
            sheet.write(row, 0, "Salesperson", section_header_fmt)
            sheet.merge_range(row, 1, row, 3, salesperson_name, section_val_fmt)
            sheet.write(row, 4, "Region", section_header_fmt)
            sheet.merge_range(row, 5, row, 7, region_name, section_val_fmt)
            row += 1

            # 2. Table Headers (Dynamic)
            row_header_detail = row

            # กำหนด Columns หลัก
            headers = [
                ("SO No.", 0),
                ("Customer", 1),
                ("Invoice No.", 2),
                ("Credit Note No.", 3),
                ("Sales Amount (Untaxed)", 4, 5),
                ("Refund Amount\n(Untaxed)", 6),
                ("Payment\n(Collected)", 7),
            ]

            # เพิ่ม Column Commission เฉพาะเมื่อ Confirm
            if wizard.is_commission_confirmed:
                headers.append(("Commission\n(Calculated)", 8))

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

            # Sub-headers for merged columns
            sheet.write(row_header_detail + 1, 4, "SO", table_header_format)
            sheet.write(row_header_detail + 1, 5, "INV", table_header_format)

            sheet.set_row(row_header_detail, 25)
            sheet.set_row(row_header_detail + 1, 25)
            row = row_header_detail + 2

            # 3. Data Lines
            # เตรียมตัวแปรเก็บ Totals (0=Sale, 1=Inv, 2=Pay, 3=Refund, 4=Comm)
            totals = [0.0, 0.0, 0.0, 0.0]
            if wizard.is_commission_confirmed:
                totals.append(0.0)

            for line in person_lines:
                so_name = line.sale_order_name or ""
                cust_name = line.customer_name or ""
                inv_name = line.invoice_name or ""
                cn_name = line.credit_note_name or ""

                amount_sale = line.amount_sale_total or 0.0
                amount_invoice = line.amount_invoice_total or 0.0
                amount_payment = line.amount_payment_total or 0.0
                amount_credit = line.amount_credit_note_total or 0.0
                amount_commission = line.amount_commission or 0.0

                sheet.write(row, 0, so_name, cell_center)
                sheet.write(row, 1, cust_name, cell_fmt)
                sheet.write(row, 2, inv_name, cell_center)
                sheet.write(row, 3, cn_name, cell_center)

                vals = [
                    amount_sale,
                    amount_invoice,
                    amount_credit,
                    amount_payment,
                ]
                if wizard.is_commission_confirmed:
                    vals.append(amount_commission)

                for i, val in enumerate(vals):
                    sheet.write(row, 4 + i, val, money_fmt)
                    totals[i] += val

                # Auto-height calculation
                inv_lines = inv_name.count("\n") + 1 if inv_name else 1
                cn_lines = cn_name.count("\n") + 1 if cn_name else 1
                height = max(25, max(inv_lines, cn_lines) * 20)
                sheet.set_row(row, height)

                row += 1

            # 4. Summary Row
            sheet.merge_range(row, 0, row, 3, "Total", sum_label)
            for i, val in enumerate(totals):
                sheet.write(row, 4 + i, val, sum_val)

            row += 2  # Gap
