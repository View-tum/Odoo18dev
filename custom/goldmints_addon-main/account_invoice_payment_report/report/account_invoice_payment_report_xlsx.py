import io
import base64
import xlsxwriter
from odoo import models, fields, api


class AccountInvoicePaymentReport(models.TransientModel):
    _inherit = "account.invoice.payment.report"

    def action_print_excel(self):
        self.ensure_one()

        query = """
            SELECT
                apm.code,
                ru.id,
                am.id,
                am.name as invoice_name,
                am.invoice_date as invoice_date,
                am.amount_total as amount_total_invoice,
                am.state,
                am.payment_state,
                aml.discount as discount_total,
                ap.date as payment_date,
                ap.amount as amount_total_payment,
                aj.type,
                CASE
                    WHEN aj.type = 'cash' THEN 'cash'
                    WHEN aj.type = 'bank' AND (
                        apm.code::text ILIKE '%%cheque%%' OR
                        apm.code::text ILIKE '%%check%%'
                    ) THEN 'cheque'
                    WHEN aj.type = 'bank' THEN 'bank'
                    ELSE 'other'
                END AS payment_type,
                rpu.id as saleperson_id,
                rpu.name as saleperson_name,
                trim(regexp_replace(regexp_replace((aj.name->>'en_US'), '^.*?-', ''),'#.*', '')) AS bank_name,
                CASE
                    WHEN (aj.name->>'en_US') LIKE '%%#%%'
                    THEN trim(regexp_replace((aj.name->>'en_US'), '^.*#\s*', '', 'g'))
                    ELSE NULL
                END AS bank_number,
                rp.ref as partner_code,
                rp.name as partner_name
            FROM 
                account_move am
                INNER JOIN lateral(
                    SELECT sum(aml.hidden_discount_amount) as discount
                    FROM account_move_line aml
                    WHERE aml.move_id = am.id
                ) aml on true
                INNER JOIN account_move__account_payment amap on amap.invoice_id = am.id
                INNER JOIN account_payment ap on ap.id = amap.payment_id
                LEFT JOIN account_journal aj on aj.id = ap.journal_id
                LEFT JOIN res_partner rp on rp.id = am.partner_id
                LEFT JOIN res_users ru on ru.id = am.invoice_user_id
                LEFT JOIN res_partner rpu on rpu.id = ru.partner_id
                LEFT JOIN account_payment_method apm on apm.id = ap.payment_method_id
            WHERE 
                am.payment_state in ('paid','in_payment')
                AND am.state = 'posted'
                AND am.move_type = 'out_invoice'
                AND ap.date >= %s
                AND ap.date <= %s
                AND ap.state = 'paid'
                AND ru.id = ANY(%s)
            ORDER BY payment_type, am.invoice_date, am.name
        """

        salesperson_list = self.salesperson_ids.ids
        # salesperson_list = tuple(self.salesperson_ids.ids)

        self.env.cr.execute(
            query, (self.date_from.date(), self.date_to.date(), salesperson_list)
        )
        results = self.env.cr.dictfetchall()

        # ตรวจสอบถ้าไม่มีข้อมูลให้แจ้งเตือน
        if not results:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "ไม่พบข้อมูล",
                    "message": "  • ไม่พบข้อมูลในการชำระเงิน",
                    "type": "danger",
                    "sticky": False,
                },
            }

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})

        # กำหนดประเภทที่จะแยก Sheet
        payment_groups = [
            {"name": "เงินสด", "type": "cash"},
            {"name": "เช็ค", "type": "cheque"},
            {"name": "เงินโอน", "type": "bank"},
            {"name": "อื่น ๆ", "type": "other"},
        ]

        # สร้าง Format (ใช้ base_style ตามเดิมของคุณ)
        base_style = {"font_name": "Angsana New", "font_size": 16}
        title_fmt = workbook.add_format(
            {**base_style, "bold": True, "align": "center", "font_size": 20}
        )
        header_fmt = workbook.add_format(
            {
                **base_style,
                "bold": True,
                "align": "center",
                "border": 1,
                "bg_color": "#D9D9D9",
            }
        )
        txt_fmt = workbook.add_format({**base_style, "border": 1, "align": "left"})
        num_fmt = workbook.add_format(
            {**base_style, "border": 1, "align": "right", "num_format": "#,##0.00"}
        )
        date_fmt = workbook.add_format(
            {**base_style, "border": 1, "align": "center", "num_format": "dd/mm/yyyy"}
        )

        for group in payment_groups:
            group_data = [r for r in results if r["payment_type"] == group["type"]]
            if not group_data:
                continue

            sheet = workbook.add_worksheet(group["name"])
            sheet.merge_range(
                0,
                0,
                0,
                13,
                f"รายงานการชำระเงิน",
                title_fmt,
            )
            sheet.write(
                1,
                0,
                f"วันที่ {self.date_from.strftime('%d/%m/%Y')} ถึง {self.date_to.strftime('%d/%m/%Y')}",
            )

            headers = [
                "วันที่ Invoice",
                "เลขที่ Invoice",
                "รหัสลูกค้า",
                "ชื่อลูกค้า",
                "ยอดตามใบแจ้งหนี้",
                "ยอดที่ชำระแล้ว",
                "พนักงานขาย",
                "วันที่รับชำระเงิน",
                "เช็ค",
                "เงินสด",
                "เงินโอน",
                "ธนาคาร",
                "ส่วนลด",
                "อื่น ๆ",
            ]
            for col, label in enumerate(headers):
                sheet.write(2, col, label, header_fmt)

            # วนลูปเขียนข้อมูลใน Sheet นั้นๆ
            row = 3
            for line in group_data:
                amt = line["amount_total_payment"] or 0.0
                sheet.write(row, 0, line["invoice_date"], date_fmt)
                sheet.write(row, 1, line["invoice_name"], txt_fmt)
                sheet.write(row, 2, line["partner_code"] or "", txt_fmt)
                sheet.write(row, 3, line["partner_name"] or "", txt_fmt)
                sheet.write(row, 4, line["amount_total_invoice"] or 0.0, num_fmt)
                sheet.write(row, 5, amt, num_fmt)
                sheet.write(row, 6, line["saleperson_name"] or "", txt_fmt)
                sheet.write(row, 7, line["payment_date"], date_fmt)

                # แสดงยอดเงินในคอลัมน์เดิมตามประเภท
                p_type = line["payment_type"]
                sheet.write(row, 8, amt if p_type == "cheque" else 0.0, num_fmt)
                sheet.write(row, 9, amt if p_type == "cash" else 0.0, num_fmt)
                sheet.write(row, 10, amt if p_type == "bank" else 0.0, num_fmt)
                sheet.write(row, 11, line["bank_number"] or "", txt_fmt)
                sheet.write(row, 12, line["discount_total"] or 0.0, num_fmt)
                sheet.write(row, 13, "", txt_fmt)
                row += 1

            # รูปแบบ: sheet.set_column(คอลัมน์แรก, คอลัมน์สุดท้าย, ความกว้าง)
            sheet.set_column(0, 1, 15)  # วันที่ และ เลขที่ Invoice
            sheet.set_column(2, 2, 12)  # รหัสลูกค้า
            sheet.set_column(3, 3, 30)  # ชื่อลูกค้า
            sheet.set_column(4, 5, 15)  # ยอดตามใบแจ้งหนี้ และ ยอดที่ชำระแล้ว
            sheet.set_column(6, 6, 20)  # พนักงานขาย
            sheet.set_column(7, 10, 15)  # วันที่รับชำระเงิน, เช็ค, เงินสด, เงินโอน
            sheet.set_column(11, 11, 25)  # ธนาคาร (กว้างหน่อยเพื่อให้เห็นเลขบัญชี)
            sheet.set_column(12, 13, 12)  # ส่วนลด, อื่น ๆ

        workbook.close()
        output.seek(0)

        file_name = f"รายงานชำระเงิน {self.date_from.strftime('%d/%m/%Y')} ถึง {self.date_to.strftime('%d/%m/%Y')}.xlsx"
        attachment = self.env["ir.attachment"].create(
            {
                "name": file_name,
                "datas": base64.b64encode(output.read()),
                "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            }
        )

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "self",
        }
