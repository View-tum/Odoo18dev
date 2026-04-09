from odoo import models


class BillingPTTXlsx(models.AbstractModel):
    _name = "report.acc_billing_ptt_template.billing_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "PTT Billing XLSX"

    def generate_xlsx_report(self, workbook, data, bills):
        sheet = workbook.add_worksheet("PTT Billing")

        # ================= Formats =================
        title_fmt = workbook.add_format({
            "font_size": 12,
            "bold": True,
            "align": "center",
            "valign": "vcenter"
        })
        
        vendor_label_fmt = workbook.add_format({
            "font_size": 11,
            "bold": True,
            "align": "center",
            "valign": "vcenter",
            "bg_color": "#000000",
            "font_color": "#FFFFFF",
            "right": 1
        })
        
        vendor_box_fmt = workbook.add_format({
            "font_size": 11,
            "align": "center",
            "valign": "vcenter",
            "border": 1
        })
        
        vendor_note_fmt = workbook.add_format({
            "font_size": 10,
            "align": "center"
        })
        
        company_label_fmt = workbook.add_format({
            "font_size": 9,
            "align": "left",
            "valign": "top"
        })
        
        day_label_fmt = workbook.add_format({
            "font_size": 11,
            "bold": True,
            "align": "center",
            "valign": "vcenter",
            "bg_color": "#000000",
            "font_color": "#FFFFFF"
        })
        
        day_input_fmt = workbook.add_format({
            "font_size": 11,
            "align": "center",
            "valign": "vcenter",
            "bottom": 1
        })
        
        partner_label_fmt = workbook.add_format({
            "font_size": 9,
            "align": "left"
        })
        
        partner_input_fmt = workbook.add_format({
            "font_size": 9,
            "align": "left",
            "bottom": 1
        })
        
        note_fmt = workbook.add_format({
            "font_size": 9,
            "align": "left"
        })
        
        header_fmt = workbook.add_format({
            "font_size": 9,
            "align": "center",
            "valign": "vcenter",
            "text_wrap": True,
            "bottom": 1
        })
        
        cell_center_fmt = workbook.add_format({
            "font_size": 9,
            "align": "center",
            "valign": "vcenter",
            "bottom": 1
        })
        
        cell_left_fmt = workbook.add_format({
            "font_size": 9,
            "align": "left",
            "valign": "vcenter",
            "bottom": 1
        })
        
        cell_right_fmt = workbook.add_format({
            "font_size": 9,
            "align": "right",
            "valign": "vcenter",
            "bottom": 1,
            "num_format": "#,##0.00"
        })
        
        total_label_fmt = workbook.add_format({
            "font_size": 9,
            "bold": True,
            "align": "center",
            "valign": "vcenter"
        })
        
        total_amount_fmt = workbook.add_format({
            "font_size": 9,
            "align": "right",
            "valign": "vcenter",
            "bottom": 6,  # Double bottom border
            "num_format": "#,##0.00"
        })
        
        instruction_header_fmt = workbook.add_format({
            "font_size": 9,
            "align": "left"
        })
        
        instruction_subheader_fmt = workbook.add_format({
            "font_size": 9,
            "align": "left"
        })
        
        instruction_fmt = workbook.add_format({
            "font_size": 9,
            "align": "left",
            "valign": "top",
            "text_wrap": True
        })
        
        banner_fmt = workbook.add_format({
            "font_size": 13,
            "bold": True,
            "align": "center",
            "valign": "vcenter",
            "bg_color": "#000000",
            "font_color": "#FFFFFF"
        })
        
        footer_note_fmt = workbook.add_format({
            "font_size": 11,
            "align": "center",
            "valign": "top",
            "text_wrap": True
        })

        instruction_header_border_fmt = workbook.add_format({
            "font_size": 9,
            "align": "left",
            "bottom": 1
        })

        # ================= Column Width (matching exactly from Excel file) =================
        sheet.set_column("A:A", 10.7)   # ลำดับ
        sheet.set_column("B:Q", 4.3)    # All columns B to Q uniform width 4.3

        row = 0

        # ================= Row 1: Main Title =================
        sheet.merge_range(row, 0, row, 16,
            "ใบรับวางบิล เฉพาะหนังสือรับรองการหักภาษี ณ ที่จ่าย - กลุ่มส่งสินค้าที่ DC PTTRM เท่านั้น",
            title_fmt
        )
        row += 2

        # ================= Row 3: Vendor Code Section =================
        sheet.merge_range(row, 6, row, 8, "รหัส vendor code", vendor_label_fmt)
        
        # Vendor boxes from columns J to Q (8 boxes)
        for i in range(8):
            sheet.write(row, 9 + i, "", vendor_box_fmt)
        
        sheet.set_row(row, 20)  # Set row height to 20
        row += 1

        # Row 4: Note for vendor code
        sheet.merge_range(row, 6, row, 16, "กรอกให้ครบ 8 หลัก", vendor_note_fmt)
        row += 2

        # ================= Row 6-9: Company Info =================
        sheet.merge_range(row, 0, row, 4, "บริษัท ปตท. บริหารธุรกิจค้าปลีก จำกัด", company_label_fmt)
        
        # วันวางบิล - merge I,J for label (columns 8,9)
        sheet.merge_range(row, 8, row, 9, "วันวางบิล", day_label_fmt)
        
        # Input area - merge K-Q (columns 10-16) with bottom border
        sheet.merge_range(row, 10, row, 16, "", day_input_fmt)
        row += 1
        
        sheet.merge_range(row, 0, row, 8, 
                         "1010 ถนนวิภาวดีรังสิต แขวงจตุจักร เขตจตุจักร กรุงเทพฯ 10900", 
                         company_label_fmt)
        row += 1
        
        sheet.merge_range(row, 0, row, 8, 
                         "โทรศัพท์: 66(0)2030-0444 / E-Mail: collection@pttrm.com", 
                         company_label_fmt)
        row += 1
        
        sheet.merge_range(row, 0, row, 5, 
                         "TAX ID : 0105537121254 สำนักงานใหญ่", 
                         company_label_fmt)
        row += 2

        # ================= Row 11-12: Partner Info =================
        sheet.write(row, 0, "จากบริษัท", partner_label_fmt)
        sheet.merge_range(row, 1, row, 12, "", partner_input_fmt)
        row += 1
        
        sheet.merge_range(row, 0, row, 1, "ชื่อ และ เบอร์ติดต่อกลับ", partner_label_fmt)
        sheet.merge_range(row, 2, row, 12, "", partner_input_fmt)
        sheet.write(row, 13, "(โปรดระบุ)", note_fmt)
        row += 2

        # ================= Row 14: Table Header =================
        sheet.write(row, 0, "ลำดับ", header_fmt)
        sheet.merge_range(row, 2, row, 4, "เลขที่ใบเสร็จรับเงิน", header_fmt)
        sheet.merge_range(row, 6, row, 8, "เลขที่หนังสือรับรองการ\nหักภาษี ณ ที่จ่าย", header_fmt)
        sheet.merge_range(row, 10, row, 12, "วันที่หนังสือรับรองการ\nหักภาษี ณ ที่จ่าย", header_fmt)
        sheet.merge_range(row, 14, row, 16, "ยอดภาษีหัก ณ\nที่จ่าย", header_fmt)
        
        sheet.set_row(row, 30)
        row += 1
        
        data_start_row = row

        # ================= Row 15-28: Data Rows (14 empty rows) =================
        for i in range(14):
            sheet.write(row, 0, "", cell_center_fmt)
            sheet.merge_range(row, 2, row, 4, "", cell_left_fmt)
            sheet.merge_range(row, 6, row, 8, "", cell_left_fmt)
            sheet.merge_range(row, 10, row, 12, "", cell_center_fmt)
            sheet.merge_range(row, 14, row, 16, "", cell_right_fmt)
            
            sheet.set_row(row, 16)
            row += 1
            
        data_end_row = row - 1

        # ================= Row 29: Total Row =================
        sheet.merge_range(row, 10, row, 12, "รวมทั้งสิ้น", total_label_fmt)
        sheet.merge_range(row, 14, row, 16, "", total_amount_fmt)
        sheet.write_formula(
            row,
            14,
            f"=SUM(O{data_start_row+1}:O{data_end_row+1})",
            total_amount_fmt
        )
        sheet.set_row(row, 16)
        row += 2

        # ================= Row 30: Instructions Header =================
        sheet.merge_range(row, 0, row, 3,
                         "แนวปฏิบัติการวางบิลค่าภาษีหัก ณ ที่จ่าย",
                         instruction_header_border_fmt)
        sheet.merge_range(row, 4, row, 8,
                         "เอกสารที่ใช้ในการวางบิลประกอบด้วย",
                         instruction_subheader_fmt)
        row += 2

        # ================= Row 31-34: Instructions =================
        instructions = [
            "1.  ใบรับวางบิลภาษีหัก ณ ที่จ่าย - กลุ่มส่งสินค้าที่ DC-PTTRM (กรอกรายละเอียดให้ครบถ้วน)",
            "2.  หนังสือรับรองการหักภาษี ณ ที่จ่าย ฉบับที่ 1 และ 2",
            "3.  สำเนาใบเสร็จรับเงินของบริษัท ปตท.บริหารธุรกิจค้าปลีก จำกัด ที่ออกให้กับท่าน"
        ]
        
        for instruction in instructions:
            sheet.merge_range(row, 0, row, 13, instruction, instruction_fmt)
            row += 1

        # Instruction 4 (2 lines)
        sheet.merge_range(row, 0, row, 13,
                         "4.  นำเอกสารข้อ 1-3 วางบิลที่ ธนาคารไทยพาณิชย์ สาขารัชโยธิน ในวันพุธที่ 2 และ 4 ของเดือน\n"
                         "     เวลา 9.00-15.00 น. ตามตารางวางบิลที่บริษัทกำหนดไว้ เท่านั้น (ไม่รับทาง Email)",
                         instruction_fmt)
        sheet.set_row(row, 30)
        row += 1

        # ================= Row 36: Banner =================
        sheet.merge_range(row, 0, row, 16,
            "วางบิลที่ธนาคารไทยพาณิชย์ สาขารัชโยธิน",
            banner_fmt)
        row += 1

        # ================= Row 37-39: Final Note =================
        final_note = (
            "ยอดชำระเงิน ธนาคารจะแจ้งทาง Email ที่ท่านแจ้งไว้ในใบเปิดหน้าบัญชี ล่วงหน้าก่อนวันครบกำหนดชำระเงิน\n"
            "หากไม่ได้รับแจ้ง โปรดสอบถามยอดเงินโอน ก่อนวันครบกำหนดชำระเงิน 1 วันเท่านั้น\n"
            "โทร : 02-030-0444 ต่อ 16440 (สงวนสิทธิ์การโทรเช็คย้อนหลัง)"
        )
        
        sheet.merge_range(row, 0, row + 2, 16, final_note, footer_note_fmt)