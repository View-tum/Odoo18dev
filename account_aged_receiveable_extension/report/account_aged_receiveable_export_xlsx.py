# -*- coding: utf-8 -*-
from odoo import models, fields, api
import io
import base64
import xlsxwriter


class AccountAgedReceiveableExportXlsx(models.AbstractModel):
    _name = "account.aged.receiveable.export.xlsx"
    _description = "Aged Receivable Excel Export Handler"

    def generate_excel(self, wizard, results):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = workbook.add_worksheet("Aged Receivable")

        base_font = "Angsana New"

        # --- Formats ---
        f_header_title = workbook.add_format(
            {
                "font_name": base_font,
                "font_size": 22,
                "bold": True,
                "align": "center",
                "valign": "vcenter",
            }
        )
        f_col_header = workbook.add_format(
            {
                "font_name": base_font,
                "font_size": 16,
                "bold": True,
                "align": "center",
                "valign": "vcenter",
                "bg_color": "#f2f2f2",
                "border": 1,
            }
        )
        f_text = workbook.add_format(
            {"font_name": base_font, "font_size": 16, "border": 1, "align": "left"}
        )
        f_date = workbook.add_format(
            {
                "font_name": base_font,
                "font_size": 16,
                "border": 1,
                "num_format": "dd/mm/yyyy",
                "align": "center",
            }
        )
        f_num = workbook.add_format(
            {
                "font_name": base_font,
                "font_size": 16,
                "border": 1,
                "num_format": "#,##0.00",
                "align": "right",
            }
        )
        f_int = workbook.add_format(
            {"font_name": base_font, "font_size": 16, "border": 1, "align": "center"}
        )
        f_total_label = workbook.add_format(
            {
                "font_name": base_font,
                "font_size": 16,
                "bold": True,
                "border": 1,
                "align": "center",
                "valign": "vcenter",
                "bg_color": "#f2f2f2",
            }
        )

        # 1. Define Columns (Clean, No Conditional)
        columns = [
            ("Partner", 30),
            ("Invoice", 20),
            ("Invoice Date", 15),
            ("Inv. Currency", 12),
            ("Payment Term", 20),
            ("Due Date", 15),
            ("Days Overdue", 12),
            ("Current", 18),
            ("1-30 Days", 18),
            ("31-60 Days", 18),
            ("61-90 Days", 18),
            ("> 90 Days", 18),
        ]

        sheet.merge_range(0, 0, 0, len(columns) - 1, "รายงานอายุลูกหนี้", f_header_title)

        for col_idx, (col_name, width) in enumerate(columns):
            sheet.write(1, col_idx, col_name, f_col_header)
            sheet.set_column(col_idx, col_idx, width)

        row = 2
        user_lang = wizard.env.user.lang or "en_US"

        for res in results:
            col = 0
            sheet.write(row, col, res.get("partner_name", ""), f_text)
            col += 1
            sheet.write(row, col, res.get("invoice_name", ""), f_text)
            col += 1
            sheet.write(row, col, res.get("invoice_date", ""), f_date)
            col += 1
            sheet.write(row, col, res.get("currency_name", ""), f_int)
            col += 1

            # Payment Term
            payment_term_val = res.get("payment_term_name", "")
            if isinstance(payment_term_val, dict):
                payment_term_val = (
                    payment_term_val.get(user_lang)
                    or payment_term_val.get("en_US")
                    or next(iter(payment_term_val.values()), "")
                )
            sheet.write(row, col, str(payment_term_val or ""), f_text)
            col += 1

            sheet.write(row, col, res.get("date_maturity", ""), f_date)
            col += 1

            # No Extra Days / Next Run here

            days_overdue = res.get("days_overdue", 0)
            sheet.write(row, col, days_overdue if days_overdue > 0 else 0, f_int)
            col += 1

            sheet.write(row, col, res.get("amount_not_due", 0.0), f_num)
            col += 1
            sheet.write(row, col, res.get("amount_1_30", 0.0), f_num)
            col += 1
            sheet.write(row, col, res.get("amount_31_60", 0.0), f_num)
            col += 1
            sheet.write(row, col, res.get("amount_61_90", 0.0), f_num)
            col += 1
            sheet.write(row, col, res.get("amount_over_90", 0.0), f_num)
            col += 1

            row += 1

        # Footer Sum
        sum_cols_count = 5
        start_sum_col_index = len(columns) - sum_cols_count

        sheet.merge_range(row, 0, row, start_sum_col_index - 1, "TOTAL", f_total_label)

        for i in range(start_sum_col_index, len(columns)):
            cell_start = xlsxwriter.utility.xl_rowcol_to_cell(2, i)
            cell_end = xlsxwriter.utility.xl_rowcol_to_cell(row - 1, i)
            sheet.write_formula(row, i, f"=SUM({cell_start}:{cell_end})", f_num)

        workbook.close()
        output.seek(0)

        filename = f"Aged_Receivable_{fields.Date.context_today(wizard)}.xlsx"
        file_content = base64.b64encode(output.read())
        output.close()

        attachment = self.env["ir.attachment"].create(
            {
                "name": filename,
                "type": "binary",
                "datas": file_content,
                "res_model": wizard._name,
                "res_id": wizard.id,
                "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            }
        )

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "new",
        }
