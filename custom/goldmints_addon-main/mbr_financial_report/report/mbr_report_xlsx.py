from odoo import models, fields
from odoo.addons.report_xlsx_helper.report.report_xlsx_format import (
    FORMATS,
    XLS_HEADERS,
)

class MBRReportXlsx(models.TransientModel):
    _name = "report.mbr_financial_report.mbr_report_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "MBR Report XLSX"

    def generate_xlsx_report(self, workbook, data, wizards):
        def pct(num, den):
            return num / den if den else 0.0

        fmt_title = workbook.add_format(
            {"bold": True, "font_size": 14, "align": "center"}
        )
        fmt_header = workbook.add_format(
            {"bold": True, "bg_color": "#DDDDDD", "border": 1, "align": "center"}
        )
        fmt_header_curr = workbook.add_format(
            {"bold": True, "bg_color": "#b7e1cd", "border": 1, "align": "center"}
        )  # light green
        fmt_header_ytd = workbook.add_format(
            {"bold": True, "bg_color": "#f8cbad", "border": 1, "align": "center"}
        )  # light orange
        fmt_head_actual = workbook.add_format(
            {"bold": True, "bg_color": "#ffe699", "border": 1, "align": "center"}
        )  # yellow
        fmt_head_budget = workbook.add_format(
            {"bold": True, "bg_color": "#c6efce", "border": 1, "align": "center"}
        )  # pale green
        fmt_head_diff = workbook.add_format(
            {"bold": True, "bg_color": "#f4b084", "border": 1, "align": "center"}
        )  # orange
        fmt_bold = workbook.add_format({"bold": True})
        fmt_num = workbook.add_format({"num_format": "#,##0", "border": 1})
        fmt_pct = workbook.add_format({"num_format": "0.0%", "border": 1})
        fmt_text = workbook.add_format({"border": 1})
        fmt_note = workbook.add_format({"border": 0})
        fmt_section = workbook.add_format({"bold": True, "bg_color": "#f2f2f2", "border": 1})
        fmt_total = workbook.add_format({"bold": True, "bg_color": "#d9e1f2", "border": 1})
        fmt_profit = workbook.add_format({"bold": True, "bg_color": "#bdd7ee", "border": 1})
        fmt_company = workbook.add_format({"bold": True, "bg_color": "#d9e2f3", "border": 1, "align": "left"})
        fmt_scale_hdr = workbook.add_format({"bg_color": "#d9e2f3", "border": 1, "align": "left"})

        for idx, wizard in enumerate(wizards):
            if idx > 0:
                break  # only generate a single sheet
            mbr = wizard.compute_mbr()

            sheet_name = "MBR %s" % (fields.Date.to_date(wizard.date_to).strftime("%Y%m%d") if hasattr(wizard, "date_to") else "Report")
            sheet = workbook.add_worksheet(sheet_name[:31])
            sheet.set_landscape()
            sheet.set_zoom(80)

            sheet.set_column("A:Z", 14)

            dataset = mbr.get("comparison") or mbr.get("main") or mbr

            def render_dataset(dataset, base_col=0):
                row = 0
                sheet.merge_range(row, base_col + 0, row, base_col + 3, wizard.company_id.name, fmt_company)
                sheet.merge_range(row, base_col + 4, row, base_col + 6, "Scale / Currency", fmt_scale_hdr)
                sheet.merge_range(row, base_col + 7, row, base_col + 12, "Divided by %s" % mbr["scale"], fmt_scale_hdr)
                row += 1

                sheet.merge_range(row, base_col + 0, row, base_col + 12, dataset["period_label"], fmt_title)
                row += 1

                sheet.write(row, base_col + 0, "Code / Description", fmt_header)
                sheet.merge_range(row, base_col + 1, row, base_col + 6, dataset["current_label"], fmt_header_curr)
                sheet.merge_range(row, base_col + 7, row, base_col + 12, dataset["ytd_label"], fmt_header_ytd)
                row += 1

                headers = [
                    "Actual",
                    "%",
                    "Budget",
                    "%",
                    "Difference",
                    "%",
                    "Actual",
                    "%",
                    "Budget",
                    "%",
                    "Difference",
                    "%",
                ]
                header_formats = [
                    fmt_head_actual,
                    fmt_head_actual,
                    fmt_head_budget,
                    fmt_head_budget,
                    fmt_head_diff,
                    fmt_head_diff,
                    fmt_head_actual,
                    fmt_head_actual,
                    fmt_head_budget,
                    fmt_head_budget,
                    fmt_head_diff,
                    fmt_head_diff,
                ]
                for idx, (label, hfmt) in enumerate(zip(headers, header_formats), start=1):
                    sheet.write(row, base_col + idx, label, hfmt)
                row += 1

                def write_line(line):
                    nonlocal row
                    indent = "    " if line["code"].startswith("1.1.") or line["code"].startswith("2.1.") else ""
                    sheet.write(row, base_col + 0, f"{indent}{line['code']} {line['name']}", fmt_text)
                    sheet.write_number(row, base_col + 1, line["curr_actual"], fmt_num)
                    sheet.write_number(row, base_col + 2, line["curr_pct_revenue"], fmt_pct)
                    sheet.write_number(row, base_col + 3, line["curr_budget"], fmt_num)
                    sheet.write_number(row, base_col + 4, line["curr_budget_pct_revenue"], fmt_pct)
                    sheet.write_number(row, base_col + 5, line["curr_diff"], fmt_num)
                    sheet.write_number(row, base_col + 6, line["curr_diff_pct"], fmt_pct)
                    sheet.write_number(row, base_col + 7, line["ytd_actual"], fmt_num)
                    sheet.write_number(row, base_col + 8, line["ytd_pct_revenue"], fmt_pct)
                    sheet.write_number(row, base_col + 9, line["ytd_budget"], fmt_num)
                    sheet.write_number(row, base_col + 10, line["ytd_budget_pct_revenue"], fmt_pct)
                    sheet.write_number(row, base_col + 11, line["ytd_diff"], fmt_num)
                    sheet.write_number(row, base_col + 12, line["ytd_diff_pct"], fmt_pct)
                    row += 1

                def write_totals_row(label, curr_actual, curr_budget, curr_diff, ytd_actual, ytd_budget, ytd_diff, fmt=None):
                    nonlocal row
                    f = fmt or fmt_bold
                    num_fmt = fmt_num if fmt is None else fmt
                    pct_fmt = fmt_pct if fmt is None else fmt
                    sheet.write(row, base_col + 0, label, f)
                    sheet.write_number(row, base_col + 1, curr_actual, num_fmt)
                    sheet.write_number(row, base_col + 2, pct(curr_actual, dataset["totals"]["total_rev_curr"]), pct_fmt)
                    sheet.write_number(row, base_col + 3, curr_budget, num_fmt)
                    sheet.write_number(row, base_col + 4, pct(curr_budget, dataset["totals"]["total_rev_curr"]), pct_fmt)
                    sheet.write_number(row, base_col + 5, curr_diff, num_fmt)
                    sheet.write_number(row, base_col + 6, pct(curr_diff, curr_budget), pct_fmt)
                    sheet.write_number(row, base_col + 7, ytd_actual, num_fmt)
                    sheet.write_number(row, base_col + 8, pct(ytd_actual, dataset["totals"]["total_rev_ytd"]), pct_fmt)
                    sheet.write_number(row, base_col + 9, ytd_budget, num_fmt)
                    sheet.write_number(row, base_col + 10, pct(ytd_budget, dataset["totals"]["total_rev_ytd"]), pct_fmt)
                    sheet.write_number(row, base_col + 11, ytd_diff, num_fmt)
                    sheet.write_number(row, base_col + 12, pct(ytd_diff, ytd_budget), pct_fmt)
                    row += 1

                sheet.write(row, base_col + 0, "1 Revenue", fmt_section)
                row += 1
                for line in [l for l in dataset["lines"] if l["section"] == "revenue"]:
                    if line["code"] == "1.1.1":
                        sheet.write(row, base_col + 0, "  1.1 Revenue from Sales", fmt_bold)
                        row += 1
                    write_line(line)
                    if line["code"] == "1.1.2":
                        write_totals_row(
                            "  Total 1.1 Revenue from Sales",
                            dataset["totals"]["total_rev_1_1_curr"],
                            dataset["totals"]["total_rev_1_1_budget_curr"],
                            dataset["totals"]["total_rev_1_1_diff_curr"],
                            dataset["totals"]["total_rev_1_1_ytd"],
                            dataset["totals"]["total_rev_1_1_budget_ytd"],
                            dataset["totals"]["total_rev_1_1_diff_ytd"],
                            fmt_bold,
                        )

                write_totals_row(
                    "(A) Total Revenue (1.1 : 1.4)",
                    dataset["totals"]["total_rev_curr"],
                    dataset["totals"]["total_rev_budget_curr"],
                    dataset["totals"]["total_rev_diff_curr"],
                    dataset["totals"]["total_rev_ytd"],
                    dataset["totals"]["total_rev_budget_ytd"],
                    dataset["totals"]["total_rev_diff_ytd"],
                    fmt_total,
                )
                row += 1

                sheet.write(row, base_col + 0, "2 Cost of Sales / Services", fmt_section)
                row += 1
                for line in [l for l in dataset["lines"] if l["section"] == "cogs"]:
                    if line["code"] == "2.1.1":
                        sheet.write(row, base_col + 0, "  2.1 Cost of Sales", fmt_bold)
                        row += 1
                    write_line(line)
                    if line["code"] == "2.1.2":
                        write_totals_row(
                            "  Total 2.1 Cost of Sales",
                            dataset["totals"]["total_cogs_2_1_curr"],
                            dataset["totals"]["total_cogs_2_1_budget_curr"],
                            dataset["totals"]["total_cogs_2_1_diff_curr"],
                            dataset["totals"]["total_cogs_2_1_ytd"],
                            dataset["totals"]["total_cogs_2_1_budget_ytd"],
                            dataset["totals"]["total_cogs_2_1_diff_ytd"],
                            fmt_bold,
                        )

                write_totals_row(
                    "(B) Total (2.1 : 2.4)",
                    dataset["totals"]["total_cogs_curr"],
                    dataset["totals"]["total_cogs_budget_curr"],
                    dataset["totals"]["total_cogs_diff_curr"],
                    dataset["totals"]["total_cogs_ytd"],
                    dataset["totals"]["total_cogs_budget_ytd"],
                    dataset["totals"]["total_cogs_diff_ytd"],
                    fmt_total,
                )

                write_totals_row(
                    "(C) Gross Profit / (Loss) (A - B)",
                    dataset["totals"]["gross_curr"],
                    dataset["totals"]["gross_budget_curr"],
                    dataset["totals"]["gross_diff_curr"],
                    dataset["totals"]["gross_ytd"],
                    dataset["totals"]["gross_budget_ytd"],
                    dataset["totals"]["gross_diff_ytd"],
                    fmt_profit,
                )
                row += 1

                sheet.write(row, base_col + 0, "3 Selling and Administrative Expenses", fmt_section)
                row += 1
                for line in [l for l in dataset["lines"] if l["section"] == "opex"]:
                    write_line(line)

                write_totals_row(
                    "(D) Total (3.1 : 3.14)",
                    dataset["totals"]["total_opex_curr"],
                    dataset["totals"]["total_opex_budget_curr"],
                    dataset["totals"]["total_opex_diff_curr"],
                    dataset["totals"]["total_opex_ytd"],
                    dataset["totals"]["total_opex_budget_ytd"],
                    dataset["totals"]["total_opex_diff_ytd"],
                    fmt_total,
                )

                write_totals_row(
                    "(E) Net Profit / (Loss) before Financial Costs (C - D)",
                    dataset["totals"]["net_before_fin_curr"],
                    dataset["totals"]["net_before_fin_budget_curr"],
                    dataset["totals"]["net_before_fin_diff_curr"],
                    dataset["totals"]["net_before_fin_ytd"],
                    dataset["totals"]["net_before_fin_budget_ytd"],
                    dataset["totals"]["net_before_fin_diff_ytd"],
                    fmt_profit,
                )
                row += 1

                sheet.write(row, base_col + 0, "4 Financial Costs", fmt_section)
                row += 1
                for line in [l for l in dataset["lines"] if l["section"] == "finance"]:
                    write_line(line)

                write_totals_row(
                    "(F) Total (4.1 : 4.2)",
                    dataset["totals"]["total_fin_curr"],
                    dataset["totals"]["total_fin_budget_curr"],
                    dataset["totals"]["total_fin_diff_curr"],
                    dataset["totals"]["total_fin_ytd"],
                    dataset["totals"]["total_fin_budget_ytd"],
                    dataset["totals"]["total_fin_diff_ytd"],
                    fmt_total,
                )

                write_totals_row(
                    "(G) Net Profit / (Loss) before Corporate Income Tax (E - F)",
                    dataset["totals"]["net_before_tax_curr"],
                    dataset["totals"]["net_before_tax_budget_curr"],
                    dataset["totals"]["net_before_tax_diff_curr"],
                    dataset["totals"]["net_before_tax_ytd"],
                    dataset["totals"]["net_before_tax_budget_ytd"],
                    dataset["totals"]["net_before_tax_diff_ytd"],
                    fmt_profit,
                )

                write_totals_row(
                    "(H) Corporate Income Tax (20%)",
                    dataset["totals"]["cit_curr"],
                    dataset["totals"]["cit_budget_curr"],
                    dataset["totals"]["cit_diff_curr"],
                    dataset["totals"]["cit_ytd"],
                    dataset["totals"]["cit_budget_ytd"],
                    dataset["totals"]["cit_diff_ytd"],
                    fmt_total,
                )

                write_totals_row(
                    "Net Profit / (Loss) after Corporate Income Tax (G - H)",
                    dataset["totals"]["net_after_tax_curr"],
                    dataset["totals"]["net_after_tax_budget_curr"],
                    dataset["totals"]["net_after_tax_diff_curr"],
                    dataset["totals"]["net_after_tax_ytd"],
                    dataset["totals"]["net_after_tax_budget_ytd"],
                    dataset["totals"]["net_after_tax_diff_ytd"],
                    fmt_profit,
                )
                row += 2

                return row

            end_row = render_dataset(dataset, base_col=0)

            # Product and customer group note block placed just after the table
            row = end_row + 1
            prod_col = 1
            cust_col = 7
            sheet.write(row, prod_col, "กลุ่มผลิตภัณฑ์", fmt_bold)
            sheet.write(row, cust_col, "กลุ่มลูกค้า", fmt_bold)
            row += 1
            sheet.write(row, prod_col, "ขายสินค้า", fmt_note)
            sheet.write(row, cust_col, "Corporate", fmt_note)
            row += 1
            sheet.write(row, prod_col, "ขายอะไหล่", fmt_note)
            sheet.write(row, cust_col, "Distributor", fmt_note)
            row += 1
            sheet.write(row, prod_col, "รวม ____________", fmt_note)
            sheet.write(row, cust_col, "E-commerce", fmt_note)
            row += 1
            sheet.write(row, cust_col, "รวม ____________", fmt_note)
            row += 2

            sheet.write(row, 0, "Scale: divided by %s" % mbr["scale"], fmt_text)
