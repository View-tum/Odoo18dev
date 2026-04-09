import io
import base64
import xlsxwriter
from odoo import models, fields, api


class AccountInvoicePaymentStatus(models.TransientModel):
    _inherit = "account.invoice.payment.status"

    def action_export_excel(self):
        self.ensure_one()
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = workbook.add_worksheet("รายงานสถานะการชำระเงิน")

        font_name = "Angsana New"
        base_style = {"font_name": font_name, "font_size": 16, "valign": "vcenter"}
        title_format = workbook.add_format(
            {**base_style, "bold": True, "align": "center", "font_size": 20}
        )
        header_format = workbook.add_format(
            {
                **base_style,
                "bold": True,
                "align": "center",
                "border": 1,
                "bg_color": "#D9D9D9",
            }
        )
        text_format = workbook.add_format({**base_style, "border": 1, "align": "left"})
        text_center_format = workbook.add_format(
            {**base_style, "border": 1, "align": "center"}
        )
        number_format = workbook.add_format(
            {**base_style, "border": 1, "align": "right", "num_format": "#,##0.00"}
        )
        date_format = workbook.add_format(
            {**base_style, "border": 1, "align": "center"}
        )

        headers = [
            "ลำดับ",
            "หมายเลข Invoice",
            "รหัสลูกค้า",
            "ลูกค้า",
            "พนักงานขาย",
            "วันที่ Invoice",
            "วันที่ครบกำหนด",
            "วันที่ชำระเงิน",
            "สกุลเงิน",
            "จำนวนเงินรวม",
            "จำนวนเงินคงเหลือ",
            "สถานะการชำระเงิน",
        ]

        sheet.merge_range(
            0, 0, 0, len(headers) - 1, "รายงานตรวจสอบสถานะใบแจ้งหนี้", title_format
        )
        sheet.set_row(0, 35)

        for col_num, header in enumerate(headers):
            sheet.write(1, col_num, header, header_format)
            if header in ["ลูกค้า"]:
                sheet.set_column(col_num, col_num, 38)
            elif header in ["พนักงานขาย"]:
                sheet.set_column(col_num, col_num, 25)
            elif header in [
                "หมายเลข Invoice",
                "วันที่ Invoice",
                "วันที่ครบกำหนด",
                "วันที่ชำระเงิน",
                "จำนวนเงินรวม",
                "จำนวนเงินคงเหลือ",
                "สถานะการชำระเงิน",
            ]:
                sheet.set_column(col_num, col_num, 18)
            elif header in ["ลำดับ", "รหัสลูกค้า", "สกุลเงิน"]:
                sheet.set_column(col_num, col_num, 10)

        status_dict = dict(self._fields["payment_state"].selection)

        row = 2
        seq = 1
        for line in self.invoice_line_ids:
            sheet.write(row, 0, seq, text_center_format)
            sheet.write(row, 1, line.invoice_name or "", text_format)
            sheet.write(row, 2, line.ref or "", text_format)
            sheet.write(row, 3, line.partner_id.name or "", text_format)
            sheet.write(row, 4, line.user_id.name or "", text_format)
            sheet.write(
                row,
                5,
                line.invoice_date.strftime("%d/%m/%Y") if line.invoice_date else "",
                date_format,
            )
            sheet.write(
                row,
                6,
                (
                    line.invoice_date_due.strftime("%d/%m/%Y")
                    if line.invoice_date_due
                    else ""
                ),
                date_format,
            )
            sheet.write(
                row,
                7,
                line.payment_date.strftime("%d/%m/%Y") if line.payment_date else "",
                date_format,
            )
            sheet.write(row, 8, line.currency_id.name or "", text_center_format)
            sheet.write(row, 9, line.amount_total, number_format)
            sheet.write(row, 10, line.amount_residual, number_format)
            thai_status = status_dict.get(line.payment_state, line.payment_state or "")
            sheet.write(row, 11, thai_status, text_center_format)

            row += 1
            seq += 1

        workbook.close()
        output.seek(0)

        file_name = f"รายงานสถานะใบแจ้งหนี้_{fields.Date.today()}.xlsx"
        attachment = self.env["ir.attachment"].create(
            {
                "name": file_name,
                "type": "binary",
                "datas": base64.b64encode(output.read()),
                "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            }
        )

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "new",
        }
