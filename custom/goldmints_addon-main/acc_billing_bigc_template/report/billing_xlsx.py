from odoo import models
import os
from odoo.modules.module import get_module_resource


class BillingBigCXlsx(models.AbstractModel):
    _name = "report.acc_billing_bigc_template.billing_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "Big C Billing XLSX"

    def generate_xlsx_report(self, workbook, data, bills):
        sheet = workbook.add_worksheet("BigC Billing")

        # ================= Formats =================
        title_fmt = workbook.add_format({
            "font_size": 11, 
            "align": "left",
            "valign": "top",
            "text_wrap": True
        })
        
        label_fmt = workbook.add_format({
            "font_size": 11, 
            "align": "left",
            "valign": "vcenter"
        })
        
        header_fmt = workbook.add_format({
            "bold": True, 
            "align": "center",
            "valign": "vcenter",
            "border": 1, 
            "text_wrap": True
        })
        
        text_fmt = workbook.add_format({
            "border": 1, 
            "font_size": 11,
            "align": "center"
        })
        
        center_fmt = workbook.add_format({
            "border": 1, 
            "align": "center", 
            "font_size": 11
        })
        
        right_fmt = workbook.add_format({
            "border": 1, 
            "align": "right", 
            "font_size": 11, 
            "num_format": "#,##0.00"
        })
        
        summary_amount_fmt = workbook.add_format({
            "font_size": 11,
            "bold": True,
            "align": "right",
            "valign": "vcenter",
            "num_format": "#,##0.00",
            "border": 1,
            "bottom": 6,  # Double bottom border
            "bottom_color": "#000000"
        })
        
        null_fmt = workbook.add_format({
            "border": 1, 
            "align": "center", 
            "valign": "vcenter",
            "font_size": 11
        })

        remark_fmt = workbook.add_format({
            "font_size": 9,
        })

        # ================= Logo =================
        logo_path = get_module_resource(
            "acc_billing_bigc_template",
            "static/img",
            "big_c_logo.png"
        )

        # ใส่โลโก้ที่ A1
        sheet.insert_image(
            "A1",
            logo_path,
            {
                "x_scale": 0.072,
                "y_scale": 0.08,
                "x_offset": 2,
                "y_offset": 2,
            }
        )

        # ================= Column Width =================
        sheet.set_column("A:A", 10)   # ลำดับที่
        sheet.set_column("B:B", 40)   # เลขที่หนังสือรับรองฯ
        sheet.set_column("C:C", 20)   # วันที่ใบเสร็จ
        sheet.set_column("D:D", 28)   # เลขที่ใบเสร็จ Big C
        sheet.set_column("E:E", 18)   # จำนวนเงิน Ex VAT
        sheet.set_column("F:F", 18)   # จำนวนเงินที่ขอคืน

        row = 0

        # ================= Header =================
        sheet.merge_range(row, 1, row + 3, 5,
            "บริษัท บิ๊กซีซูเปอร์เซ็นเตอร์ จำกัด (มหาชน)\n"
            "Finance & Accounting Division\n"
            "97/11 ชั้น 6 ถ.ราชดำริห์ แขวงลุมพินี เขตปทุมวัน กรุงเทพฯ 10330\n"
            "Tel. 02-6550666 Fax. 02-6503697-8",
            title_fmt
        )
        
        row += 5

        sheet.merge_range(row, 1, row, 5,
            "ใบสรุปการนำส่งหนังสือรับรองการหักภาษี ณ ที่จ่าย",
            title_fmt
        )
        
        row += 2

        # ================= Partner Info =================
        sheet.write(row, 0, "วันที่นำส่ง", label_fmt)
        sheet.write(row, 1, "______________________________", label_fmt)
        row += 1
        sheet.write(row, 0, "รหัสลูกค้า", label_fmt)
        sheet.write(row, 1, "6000340", label_fmt)
        row += 1
        sheet.write(row, 0, "ชื่อร้านค้า", label_fmt)
        sheet.write(row, 1, "บริษัท โกลด์ มินท์ โปรดักส์ จํากัด", label_fmt)
        row += 1
        sheet.write(row, 0, "ชื่อผู้ติดต่อ", label_fmt)
        sheet.write(row, 1, "คุณสุวนันท์, คุณนิธิดา (แผนกบัญชี)", label_fmt)
        row += 1
        sheet.write(row, 0, "เบอร์โทร", label_fmt)
        sheet.write(row, 1, "02 7448497-8", label_fmt)
        row += 1
        sheet.write(row, 0, "E-MAIL", label_fmt)
        sheet.write(row, 1, "pravitgmp@yahoo.com", label_fmt)
        row += 2

        # ================= Table Header =================
        headers = [
            "ลำดับที่",
            "เลขที่หนังสือรับรองการหัก ภาษี ณ ที่จ่าย",
            "วันที่ในเสร็จรับเงิน",
            "เลขที่ในเสร็จรับเงินของ Big C",
            "จำนวนเงิน Ex Vat",
            "จำนวนเงินที่ขอคืน",
        ]
        for col, h in enumerate(headers):
            sheet.write(row, col, h, header_fmt)
        
        sheet.set_row(row, 30)  # Set header row height
        row += 1
        
        data_start_row = row

        # ================= Data Rows (18 empty rows) =================
        for i in range(18):
            sheet.write(row, 0, "", center_fmt)
            sheet.write(row, 1, "", text_fmt)
            sheet.write(row, 2, "", center_fmt)
            sheet.write(row, 3, "", text_fmt)
            sheet.write(row, 4, "", right_fmt)
            sheet.write(row, 5, "", right_fmt)
            
            sheet.set_row(row, 25)  # Set data row height to 25
            row += 1
        
        data_end_row = row - 1

        # ================= Summary =================
        sheet.write(row, 0, "", null_fmt)
        sheet.write(row, 1, "", null_fmt)
        sheet.write(row, 2, "", null_fmt)
        sheet.write(row, 3, "จำนวนเงินรวม", null_fmt)
        sheet.write(row, 4, f"=SUM(E{data_start_row+1}:E{data_end_row+1})", summary_amount_fmt)
        sheet.write(row, 5, f"=SUM(F{data_start_row+1}:F{data_end_row+1})", summary_amount_fmt)
        sheet.set_row(row, 25)

        # ================= Footer =================
        row += 2
        sheet.merge_range(
            row, 0, row, 5,
            "หมายเหตุ วางบิลหนังสือรับรองการหัก ณ ที่จ่าย นับจากวันที่ออกหนังสือรับรองไม่เกิน 60 วัน ออกหนังสือรับรองภาษี ณ ที่จ่ายเมื่อใบแจ้งหนี้มีการหักบัญชีแล้วเท่านั้น",
            remark_fmt
        )
        row += 2
        sheet.write(row, 0, "ผู้ส่ง ........................................")
        row += 1
        sheet.write(row, 0, "วันที่ ........................................")