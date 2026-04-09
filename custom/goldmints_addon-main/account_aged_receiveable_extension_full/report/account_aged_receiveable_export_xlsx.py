# -*- coding: utf-8 -*-
from odoo import models, fields, api
import io, base64, xlsxwriter, re
from datetime import timedelta


class AccountAgedReceiveableExportXlsx(models.AbstractModel):
    _inherit = "account.aged.receiveable.export.xlsx"

    def generate_excel(self, wizard, results):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = workbook.add_worksheet("รายงานอายุลูกหนี้")
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

        # กำหนดคอลัมน์ตามลำดับใหม่
        columns = [
            ("วันที่ใบแจ้งหนี้", 15),
            ("วันที่ส่งของ", 15),
            ("Invoice", 20),
            ("Sales order", 20),
            ("รหัสลูกค้า", 12),
            ("ชื่อลูกค้า", 30),
            ("จำนวนเงิน", 15),
            ("เงื่อนไขการชำระเงิน", 20),
        ]

        if wizard.payment_term_extension == "Payment Term Sales":
            columns.append(("วันพิเศษ", 10))
        elif wizard.payment_term_extension == "Payment Term Customer":
            columns.append(("วันที่รันถัดไป", 15))

        columns.extend(
            [
                ("พนักงานขาย", 20),
                ("จำนวนวันเกินกำหนด", 18),
                ("ยอดที่ยังไม่ถึงกำหนดชำระ", 22),
                ("1-30 วัน", 18),
                ("31-60 วัน", 18),
                ("61-90 วัน", 18),
                ("เกิน 90 วัน", 18),
                (wizard.date_at.strftime("%d/%m/%Y"), 15),
                ("ช่วงระยะเวลาเครดิต", 20),
                ("หมายเหตุ", 20),
            ]
        )

        sheet.merge_range(0, 0, 0, len(columns) - 1, "รายงานอายุลูกหนี้", f_header_title)
        sheet.merge_range(
            1,
            0,
            1,
            len(columns) - 1,
            "ณ วันที่ " + wizard.date_at.strftime("%d/%m/%Y"),
            f_header_title,
        )

        for col_idx, (col_name, width) in enumerate(columns):
            sheet.write(2, col_idx, col_name, f_col_header)
            sheet.set_column(col_idx, col_idx, width)

        row = 3

        for res in results:
            col = 0
            # 0. วันที่ Invoice
            inv_date = res.get("invoice_date")
            sheet.write(row, col, inv_date, f_date)
            col += 1

            # 1. วันที่ส่งของ (สมมติ Invoice + 1)
            delivery_date = inv_date + timedelta(days=1) if inv_date else ""
            sheet.write(row, col, delivery_date, f_date)
            col += 1

            # 2. Invoice Name / 3. SO Name / 4. Customer Code / 5. Customer Name
            sheet.write(row, col, res.get("invoice_name", ""), f_text)
            col += 1
            sheet.write(row, col, res.get("sale_order_name", ""), f_text)
            col += 1
            sheet.write(row, col, res.get("partner_ref", ""), f_text)
            col += 1
            sheet.write(row, col, res.get("partner_name", ""), f_text)
            col += 1
            sheet.write(row, col, res.get("amount_residual", 0.0), f_num)
            col += 1

            if wizard.payment_term_extension == "Payment Term Default":
                Payment_Term = (
                    res.get("date_maturity") - res.get("invoice_date")
                    if res.get("date_maturity") and res.get("invoice_date")
                    else 0
                )
            elif wizard.payment_term_extension == "Payment Term Sales":
                invoice_due_date = res.get("date_maturity") + timedelta(
                    days=res.get("extra_days", 0)
                )
                Payment_Term = (
                    (invoice_due_date - res.get("invoice_date")).days
                    if invoice_due_date and res.get("invoice_date")
                    else 0
                )
            elif wizard.payment_term_extension == "Payment Term Customer":
                Payment_Term = (
                    (res.get("next_run_date") - res.get("invoice_date")).days
                    if res.get("next_run_date") and res.get("invoice_date")
                    else 0
                )
            sheet.write(row, col, Payment_Term, f_int)
            col += 1

            # Extra Columns (7. ถ้ามี)
            if wizard.payment_term_extension == "Payment Term Sales":
                sheet.write(row, col, res.get("extra_days", 0), f_int)
                col += 1
            elif wizard.payment_term_extension == "Payment Term Customer":
                sheet.write(row, col, res.get("next_run_date"), f_date)
                col += 1

            # Salesperson / Days Overdue
            sheet.write(row, col, res.get("salesperson_name", ""), f_text)
            col += 1
            sheet.write(row, col, max(res.get("days_overdue", 0), 0), f_int)
            col += 1

            # เก็บตำแหน่งเริ่มต้นยอดเงินเพื่อใช้ทำ SUM
            amount_start_col = col

            # Amounts (5 ช่วงเวลา)
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

            diff_days_new = 0
            if delivery_date:
                new_due_date = delivery_date + timedelta(days=Payment_Term.days)
                diff_days_new = (new_due_date - wizard.date_at).days
            diff_cell = xlsxwriter.utility.xl_rowcol_to_cell(row, col)
            sheet.write(row, col, diff_days_new, f_int)
            col += 1

            # Credit Term & Note
            pt_days = (
                Payment_Term.days
                if hasattr(Payment_Term, "days")
                else int(Payment_Term)
            )
            credit_term_formula = ""
            if pt_days == 0:
                if wizard.region_type == "bkk":
                    credit_term_formula = f'=IF({diff_cell}>=0,"ยังไม่ถึงกำหนดชำระ",IF({diff_cell}>=-2,"กำหนดชำระ 1-2 วัน","เกินกำหนดชำระ"))'
                elif wizard.region_type == "upc":
                    credit_term_formula = f'=IF({diff_cell}>=0,"ยังไม่ถึงกำหนดชำระ",IF({diff_cell}>=-10,"กำหนดชำระ 1-10 วัน","เกินกำหนดชำระ"))'
            elif pt_days == 7:
                if wizard.region_type == "bkk":
                    credit_term_formula = f'=IF({diff_cell}>=0,"ยังไม่ถึงกำหนดชำระ",IF({diff_cell}>=-23,"กำหนดชำระ 7-30 วัน","เกินกำหนดชำระ"))'
                elif wizard.region_type == "upc":
                    credit_term_formula = f'=IF({diff_cell}>=0,"ยังไม่ถึงกำหนดชำระ",IF({diff_cell}>=-83,"กำหนดชำระ 7-90 วัน","เกินกำหนดชำระ"))'
            elif pt_days == 30:
                if wizard.region_type == "bkk":
                    credit_term_formula = f'=IF({diff_cell}>=0,"ยังไม่ถึงกำหนดชำระ",IF({diff_cell}>=-15,"กำหนดชำระ 30-45 วัน","เกินกำหนดชำระ"))'
                elif wizard.region_type == "upc":
                    credit_term_formula = f'=IF({diff_cell}>=0,"ยังไม่ถึงกำหนดชำระ",IF({diff_cell}>=-60,"กำหนดชำระ 30-90 วัน","เกินกำหนดชำระ"))'
            elif pt_days == 60:
                if wizard.region_type == "bkk":
                    credit_term_formula = f'=IF({diff_cell}>=0,"ยังไม่ถึงกำหนดชำระ",IF({diff_cell}>=-60,"กำหนดชำระ 60-120 วัน","เกินกำหนดชำระ"))'
                elif wizard.region_type == "upc":
                    credit_term_formula = f'=IF({diff_cell}>=0,"ยังไม่ถึงกำหนดชำระ",IF({diff_cell}>=-120,"กำหนดชำระ 60-120 วัน","เกินกำหนดชำระ"))'

            if credit_term_formula:
                sheet.write_formula(row, col, credit_term_formula, f_text, value="")
            else:
                sheet.write(row, col, "", f_text)
            col += 1
            sheet.write(row, col, "", f_text)
            row += 1

        for i in range(amount_start_col, amount_start_col + 5):
            cell_start = xlsxwriter.utility.xl_rowcol_to_cell(3, i)
            cell_end = xlsxwriter.utility.xl_rowcol_to_cell(row - 1, i)
            sheet.write_formula(row, i, f"=SUM({cell_start}:{cell_end})", f_num)

        workbook.close()
        output.seek(0)
        filename = f"รายงานอายุลูกหนี้ ณ วันที่ {wizard.date_at.strftime('%d-%m-%Y')}.xlsx"
        file_content = base64.b64encode(output.read())
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
