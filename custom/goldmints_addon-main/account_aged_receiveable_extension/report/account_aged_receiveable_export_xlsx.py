# -*- coding: utf-8 -*-
from odoo import models, fields, api
import io
import base64
import xlsxwriter
from datetime import timedelta


class AccountAgedReceiveableExportXlsx(models.AbstractModel):
    _name = "account.aged.receiveable.export.xlsx"
    _description = "Aged Receivable Excel Export Handler"

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
        f_total_label = workbook.add_format(
            {
                "font_name": base_font,
                "font_size": 16,
                "bold": True,
                "border": 1,
                "align": "center",
                "bg_color": "#f2f2f2",
            }
        )

        # กำหนดคอลัมน์ตามลำดับใหม่
        columns = [
            ("วันที่ใบแจ้งหนี้", 15),
            ("วันที่ส่งของ", 15),
            ("Invoice", 20),
            ("Sales order", 20),
            ("รหัสลูกค้า", 12),
            ("ชื่อลูกค้า", 30),
            ("เงื่อนไขการชำระเงิน", 20),
            ("พนักงานขาย", 20),
            ("จำนวนวันเกินกำหนด", 18),
            ("ยอดที่ยังไม่ถึงกำหนดชำระ", 22),
            ("1-30 วัน", 18),
            ("31-60 วัน", 18),
            ("61-90 วัน", 18),
            ("เกิน 90 วัน", 18),
            ("ช่วงระยะเวลาเครดิต", 20),
            ("หมายเหตุ", 20),
        ]

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

            # วันที่ Invoice
            col = 0
            inv_date = res.get("invoice_date")
            sheet.write(row, col, inv_date, f_date)

            # วันที่ส่งของ (สมมติเป็นวันที่ Invoice + 1 วัน)
            col += 1
            delivery_date = inv_date + timedelta(days=1) if inv_date else ""
            sheet.write(row, col, delivery_date, f_date)

            # Invoice Name
            col += 1
            sheet.write(row, col, res.get("invoice_name", ""), f_text)

            # Sales Order Name
            col += 1
            # so_name = (
            #     self.env["sale.order"].browse(res.get("sale_order_id")).name
            #     if res.get("sale_order_id")
            #     else ""
            # )
            so_name = res.get("sale_order_name") or ""
            sheet.write(row, col, so_name, f_text)

            # Customer Code
            col += 1
            sheet.write(row, col, res.get("partner_ref", ""), f_text)

            # Customer Name
            col += 1
            sheet.write(row, col, res.get("partner_name", ""), f_text)

            # Payment Term
            col += 1
            payment_term_val = res.get("payment_term_name", "")
            if isinstance(payment_term_val, dict):
                user_lang = wizard.env.user.lang or "en_US"
                payment_term_val = (
                    payment_term_val.get(user_lang)
                    or payment_term_val.get("en_US")
                    or next(iter(payment_term_val.values()), "")
                )
            sheet.write(row, col, str(payment_term_val or ""), f_text)

            # Salesperson
            col += 1
            sheet.write(row, col, res.get("salesperson_name") or "", f_text)

            # Days Overdue & Amounts
            col += 1
            sheet.write(row, col, res.get("days_overdue", 0), f_int)
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

            # Credit Term & Note
            col += 1
            sheet.write(row, col, "", f_text)
            col += 1
            sheet.write(row, col, "", f_text)
            col += 1
            row += 1

        # Sum Formula (รวมยอด 5 ช่วงเวลาท้ายสุด)
        for i in range(9, 14):
            cell_start = xlsxwriter.utility.xl_rowcol_to_cell(2, i)
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
