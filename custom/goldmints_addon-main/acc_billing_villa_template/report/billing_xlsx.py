from odoo import models


class BillingVillaXlsx(models.AbstractModel):
    _name = "report.acc_billing_villa_template.billing_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "Villa Billing XLSX"

    def generate_xlsx_report(self, workbook, data, bills):
        sheet = workbook.add_worksheet("Villa Billing")

        # ================= Formats =================
        company_info_fmt = workbook.add_format({
            "font_size": 11,
            "align": "center",
            "valign": "vcenter",
            "text_wrap": True
        })
        
        title_fmt = workbook.add_format({
            "font_size": 16,
            "bold": True,
            "align": "center",
            "valign": "vcenter"
        })
        
        subtitle_fmt = workbook.add_format({
            "font_size": 11,
            "align": "right",
            "valign": "vcenter"
        })
        
        date_label_fmt = workbook.add_format({
            "font_size": 11,
            "align": "left",
            "valign": "vcenter"
        })
        
        date_value_fmt = workbook.add_format({
            "font_size": 11,
            "align": "left",
            "valign": "vcenter"
        })
        
        recipient_info_fmt = workbook.add_format({
            "font_size": 11,
            "align": "left",
            "valign": "top",
            "text_wrap": True
        })
        
        header_fmt = workbook.add_format({
            "font_size": 11,
            "align": "center",
            "valign": "vcenter",
            "border": 1,
            "text_wrap": True
        })
        
        cell_center_fmt = workbook.add_format({
            "font_size": 11,
            "align": "center",
            "valign": "vcenter",
            "left": 1,
            "right": 1,
            "bottom": 1
        })
        
        cell_left_fmt = workbook.add_format({
            "font_size": 11,
            "align": "left",
            "valign": "vcenter",
            "left": 1,
            "right": 1,
            "bottom": 1
        })
        
        cell_right_fmt = workbook.add_format({
            "font_size": 11,
            "align": "right",
            "valign": "vcenter",
            "left": 1,
            "right": 1,
            "bottom": 1,
            "num_format": "#,##0.00"
        })
        
        summary_label_fmt = workbook.add_format({
            "font_size": 11,
            "align": "center",
            "valign": "vcenter",
            "border": 1
        })
        
        summary_amount_fmt = workbook.add_format({
            "font_size": 11,
            "bold": True,
            "align": "right",
            "valign": "vcenter",
            "border": 1,
            "num_format": "#,##0.00"
        })
        
        signature_box_fmt = workbook.add_format({
            "font_size": 11,
            "align": "left",
            "valign": "vcenter",
            "border": 1
        })

        summary_left_fmt = workbook.add_format({
            "font_size": 11,
            "align": "left",
            "valign": "vcenter",
            "top": 1,
            "bottom": 1,
            "left": 1
        })

        summary_center_fmt = workbook.add_format({
            "font_size": 11,
            "align": "center",
            "valign": "vcenter",
            "top": 1,
            "bottom": 1,
            "right": 1
        })

        summary_amount_fmt = workbook.add_format({
            "font_size": 11,
            "bold": True,
            "align": "right",
            "valign": "vcenter",
            "num_format": "#,##0.00",
            "border": 1,
            "bottom": 6   # เส้นคู่ด้านล่าง
        })

        box_left_label_fmt = workbook.add_format({
            "font_size": 11,
            "align": "left",
            "valign": "vcenter",
            "top": 1,
            "bottom": 1,
            "left": 1
        })

        box_left_value_fmt = workbook.add_format({
            "font_size": 11,
            "align": "left",
            "valign": "vcenter",
            "top": 1,
            "bottom": 1,
            "right": 1
        })

        # ================= Column Width =================
        sheet.set_column("A:A", 8)    # ลำดับที่
        sheet.set_column("B:B", 14)   # เล่มที่ INVOICE
        sheet.set_column("C:C", 16)   # เลขที่ INVOICE
        sheet.set_column("D:D", 13)   # ลงวันที่
        sheet.set_column("E:E", 16)   # จำนวนเงินสุทธิ
        sheet.set_column("F:F", 40)   # หมายเหตุ

        row = 0

        # ================= Header: Company Info =================
        sheet.merge_range(row, 0, row, 5,
            "บริษัท โกลด์ มิ้นท์ โปรดักส์ จำกัด(สนญ.)",
            company_info_fmt
        )
        row += 1
        
        sheet.merge_range(row, 0, row, 5,
            "ที่อยู่ 248/1 ถ.เลียบทางด่วน แขวงบางนาเหนือ เขตบางนา กทม. 10260",
            company_info_fmt
        )
        row += 1
        
        sheet.merge_range(row, 0, row, 5,
            "เลขประจำตัวผู้เสียภาษี : 0105532084750",
            company_info_fmt
        )
        row += 1

        # ================= Title =================
        sheet.merge_range(row, 0, row, 5,
            "ใบวางบิล",
            title_fmt
        )
        row += 1

        # ================= Subtitle (วันที่) =================
        sheet.merge_range(row, 0, row, 3, "", date_label_fmt)
        sheet.write(row, 4, "วันที่", subtitle_fmt)
        sheet.write(row, 5, "", date_value_fmt)
        row += 1

        # ================= Recipient Info =================
        sheet.merge_range(row, 0, row + 2, 5,
            "ได้วางบิลให้กับ บริษัท วิลล่า มาร์เก็ต เจพี จำกัด เลขประจำตัวผู้เสียภาษี : 0105531013646\n"
            "ที่อยู่ : เลขที่ 496-502 อาคารเกษรอัมรินทร์ ถนนเพลินจิต แขวงลุมพินี เขตปทุมวัน กรุงเทพมหานคร 10330\n"
            "มีรายละเอียดดังต่อไปนี้ :-",
            recipient_info_fmt
        )
        row += 3

        # ================= Table Header =================
        sheet.write(row, 0, "ลำดับที่", header_fmt)
        sheet.write(row, 1, "เล่มที่ INVOICE", header_fmt)
        sheet.write(row, 2, "เลขที่ INVOICE", header_fmt)
        sheet.write(row, 3, "ลงวันที่", header_fmt)
        sheet.write(row, 4, "จำนวนเงินสุทธิ", header_fmt)
        sheet.write(row, 5, "หมายเหตุ", header_fmt)
        
        sheet.set_row(row, 20)
        row += 1
        
        data_start_row = row

        # ================= Data Rows (25 empty rows) =================
        for i in range(25):
            sheet.write(row, 0, "", cell_center_fmt)
            sheet.write(row, 1, "", cell_center_fmt)
            sheet.write(row, 2, "", cell_left_fmt)
            sheet.write(row, 3, "", cell_center_fmt)
            sheet.write(row, 4, "", cell_right_fmt)
            sheet.write(row, 5, "", cell_left_fmt)

            sheet.set_row(row, 20)
            row += 1
        
        data_end_row = row - 1

        # ================= Summary Row =================
        sheet.merge_range(row, 0, row, 1, "", summary_left_fmt)
        sheet.write_formula(
            row,
            0,
            f'="รวม " & COUNTA(A{data_start_row+1}:A{data_end_row+1}) & " ฉบับ"',
            summary_left_fmt
        )
        sheet.merge_range(row, 2, row, 3, "จำนวนเงินรวม", summary_center_fmt)
        sheet.write_formula(
            row,
            4,
            f"=SUM(E{data_start_row+1}:E{data_end_row+1})",
            summary_amount_fmt
        )
        sheet.write(row, 5, "", summary_label_fmt)
        
        sheet.set_row(row, 20)
        row += 2

        # ================= Footer Signature Boxes =================
        # ผู้วางบิล
        sheet.write(row, 0, "ผู้วางบิล", box_left_label_fmt)
        sheet.write(row, 1, "", box_left_value_fmt)

        # ผู้รับวางบิล (ฝั่งขวา)
        sheet.write(row, 3, "ผู้รับวางบิล", box_left_label_fmt)
        sheet.write(row, 4, "", box_left_value_fmt)

        sheet.set_row(row, 20)
        row += 1

        # วันที่
        sheet.write(row, 0, "วันที่", box_left_label_fmt)
        sheet.write(row, 1, "", box_left_value_fmt)

        # กำหนดรับเงินวันที่
        sheet.write(row, 3, "กำหนดรับเงินวันที่", box_left_label_fmt)
        sheet.write(row, 4, "", box_left_value_fmt)
        
        sheet.set_row(row, 20)