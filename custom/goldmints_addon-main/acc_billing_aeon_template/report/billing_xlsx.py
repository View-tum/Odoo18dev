from odoo import models


class BillingAeonXlsx(models.AbstractModel):
    _name = "report.acc_billing_aeon_template.billing_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "Aeon Billing XLSX"

    def generate_xlsx_report(self, workbook, data, bills):
        sheet = workbook.add_worksheet("Aeon Billing")

        # ================= Formats =================
        title_fmt = workbook.add_format({
            "font_size": 11,
            "bold": True,
            "align": "left",
            "valign": "vcenter"
        })
        
        note_right_fmt = workbook.add_format({
            "font_size": 9,
            "align": "right",
            "valign": "vcenter",
            "text_wrap": True
        })
        
        label_bold_fmt = workbook.add_format({
            "font_size": 11,
            "bold": True,
            "align": "left",
            "valign": "vcenter"
        })
        
        label_fmt = workbook.add_format({
            "font_size": 11,
            "align": "left",
            "valign": "vcenter"
        })
        
        label_small_fmt = workbook.add_format({
            "font_size": 9,
            "align": "left",
            "valign": "vcenter"
        })
        
        label_tiny_fmt = workbook.add_format({
            "font_size": 8,
            "align": "left",
            "valign": "vcenter"
        })
        
        input_line_fmt = workbook.add_format({
            "font_size": 9,
            "align": "center",
            "valign": "bottom"
        })
        
        payment_bold_fmt = workbook.add_format({
            "font_size": 9,
            "bold": True,
            "align": "center",
            "valign": "vcenter"
        })
        
        header_fmt = workbook.add_format({
            "font_size": 9,
            "align": "center",
            "valign": "vcenter",
            "border": 1,
            "text_wrap": True
        })

        sub_header_fmt = workbook.add_format({
            "font_size": 9,
            "align": "center",
            "valign": "vcenter",
            "left": 1,
            "right": 1,
            "bottom": 1,
            "text_wrap": True
        })
        
        cell_center_fmt = workbook.add_format({
            "font_size": 9,
            "align": "center",
            "valign": "vcenter",
            "border": 1
        })
        
        cell_left_fmt = workbook.add_format({
            "font_size": 9,
            "align": "left",
            "valign": "vcenter",
            "border": 1
        })
        
        cell_right_fmt = workbook.add_format({
            "font_size": 9,
            "align": "right",
            "valign": "vcenter",
            "border": 1,
            "num_format": "#,##0.00"
        })
        
        summary_label_fmt = workbook.add_format({
            "font_size": 9,
            "align": "left",
            "valign": "vcenter",
            "border": 1
        })
        
        summary_value_fmt = workbook.add_format({
            "font_size": 9,
            "align": "right",
            "valign": "vcenter",
            "border": 1,
            "num_format": "#,##0.00"
        })
        
        summary_int_fmt = workbook.add_format({
            "font_size": 9,
            "align": "center",
            "valign": "vcenter",
            "border": 1,
            "num_format": "#,##0"
        })
        
        footer_title_fmt = workbook.add_format({
            "font_size": 8,
            "align": "left",
            "valign": "vcenter",
            "underline": True
        })
        
        footer_subtitle_fmt = workbook.add_format({
            "font_size": 8,
            "align": "left",
            "valign": "vcenter",
            "underline": True
        })
        
        footer_text_fmt = workbook.add_format({
            "font_size": 8,
            "align": "left",
            "valign": "top",
            "text_wrap": True
        })
        
        footer_text_fmt_vcenter = workbook.add_format({
            "font_size": 8,
            "align": "left",
            "valign": "vcenter",
            "text_wrap": True
        })
        
        footer_number_fmt = workbook.add_format({
            "font_size": 8,
            "align": "center",
            "valign": "vcenter"
        })
        
        footer_bold_fmt = workbook.add_format({
            "font_size": 8,
            "bold": True,
            "align": "left",
            "valign": "vcenter",
            "text_wrap": True
        })
        
        footer_small_fmt = workbook.add_format({
            "font_size": 7,
            "align": "left",
            "valign": "vcenter"
        })

        # ===== Special formats for border control =====

        # ชิดล่าง ไม่มีขอบ
        bottom_align_no_border_fmt = workbook.add_format({
            "font_size": 10,
            "align": "left",
            "valign": "bottom",
            "text_wrap": True,
            "top": 1,
            "left": 1,
            "right": 1
        })

        bottom_align_small_no_border_fmt = workbook.add_format({
            "font_size": 8,
            "align": "left",
            "valign": "bottom"
        })

        # ชิดล่าง + เส้นขอบล่าง
        bottom_align_bottom_border_fmt = workbook.add_format({
            "font_size": 8,
            "align": "center",
            "valign": "bottom",
            "bottom": 1,
            "bg_color": "#D3D3D3"
        })

        # เส้นซ้าย + ล่าง
        left_bottom_border_fmt = workbook.add_format({
            "font_size": 8,
            "valign": "bottom",
            "left": 1,
            "bottom": 1
        })

        # เส้นขวา + ล่าง
        right_bottom_border_fmt = workbook.add_format({
            "font_size": 8,
            "valign": "bottom",
            "right": 1,
            "bottom": 1
        })

        # Header เทา ไม่มีเส้นล่าง
        header_gray_no_bottom_fmt_payment = workbook.add_format({
            "font_size": 9,
            "align": "center",
            "valign": "vcenter",
            "bg_color": "#D3D3D3",
            "top": 1,
            "left": 1
        })

        header_gray_no_bottom_fmt_checked = workbook.add_format({
            "font_size": 9,
            "align": "center",
            "valign": "vcenter",
            "bg_color": "#D3D3D3",
            "top": 1,
            "right": 1,
            "left": 1
        })

        # Company box ไม่มีเส้นล่าง
        company_box_no_bottom_fmt = workbook.add_format({
            "font_size": 10,
            "align": "left",
            "valign": "top",
            "text_wrap": True,
            "left": 1,
            "right": 1,
            "top": 1
        })

        # Rebate note มีเส้น ซ้าย ขวา ล่าง
        rebate_note_border_fmt = workbook.add_format({
            "font_size": 8,
            "align": "right",
            "valign": "vcenter",
            "left": 1,
            "right": 1,
            "bottom": 1
        })

        # ================= Column Width (ตามไฟล์ Excel) =================
        sheet.set_column("A:A", 4)      # Column A
        sheet.set_column("B:W", 3)      # Columns B-W
        sheet.set_column("X:X", 0.5)    # Column X
        sheet.set_column("Y:Y", 3)      # Column Y
        sheet.set_column("AA:AA", 4.5)  # Column AA
        sheet.set_column("Z:AD", 3)     # Columns Z-AD

        row = 0

        # ================= Row 1: Title =================
        sheet.merge_range(row, 0, row, 9,
            "ใบสรุปใบการส่งเอกสาร(ใบเตรียมวางบิล)",
            title_fmt
        )
        
        sheet.merge_range(row, 15, row, 29,
            "ทำใบสรุปฯ 2 ฉบับ-อิออนฯจะเซ็นรับทั้งสองฉบับและจะคืนให้เป็นหลักฐานหนึ่งฉบับ",
            note_right_fmt
        )
        sheet.set_row(row, 13.8)
        row += 2

        # ================= Row 3: จาก =================
        sheet.write(row, 0, "จาก", label_bold_fmt)  # A3
        sheet.merge_range(row, 1, row, 5, "ชื่อ/ที่อยู่ บริษัท, บุคคล", label_fmt)  # B3:F3
        sheet.merge_range(row, 8, row, 19, "..............................................................................", input_line_fmt)  # I3:R3
        row += 1
        
        # ================= Row 4: ผู้วางบิล =================
        sheet.merge_range(row, 0, row, 1, "ผู้วางบิล", label_small_fmt)  # A4:B4
        sheet.merge_range(row, 2, row, 4, ".........................", input_line_fmt)  # C4:E4
        sheet.write(row, 8, "วันที่", label_small_fmt)  # I4
        sheet.merge_range(row, 9, row, 10, ".............", input_line_fmt)  # J4:K4
        sheet.write(row, 12, "เบอร์โทร", label_small_fmt)  # M4
        sheet.merge_range(row, 16, row, 17, "….............", input_line_fmt)  # Q4:R4
        sheet.merge_range(row, 18, row, 22, "ชื่อผู้ติดต่อ(บัญชีหรือฝ่าย)", label_small_fmt)  # S4:W4
        sheet.merge_range(row, 25, row, 26, "e-mail", input_line_fmt)  # Z4:AA4
        row += 1
        
        # ================= Row 5: รหัสผู้จำหน่าย =================
        sheet.merge_range(row, 0, row, 2, "รหัสผู้จำหน่าย", label_small_fmt)  # A5:C5
        sheet.merge_range(row, 3, row, 6, ".........................", input_line_fmt)  # D5:G5
        sheet.write(row, 9, "เครดิต", workbook.add_format({
            "font_size": 8,
            "align": "right",
            "valign": "vcenter"
        }))  # J5 - align right!
        sheet.merge_range(row, 10, row, 11, ".................", input_line_fmt)  # K5:L5
        sheet.write(row, 12, "วัน", label_tiny_fmt)  # M5
        row += 1
        
        # ================= Row 6: Payment method =================
        sheet.merge_range(row, 0, row, 9,
            "รับชำระเงินโดย_โอนเงินผ่านธนาคาร..(ลบธนาคารที่ไม่ใช่ออก)",
            label_small_fmt
        )  # A6:J6
        sheet.merge_range(row, 11, row, 13, "BBL=กรุงเทพ", payment_bold_fmt)  # L6:N6
        sheet.write(row, 16, "หรือ", label_small_fmt)  # Q6
        sheet.merge_range(row, 19, row, 21, "KKB=กสิกร", payment_bold_fmt)  # T6:V6
        sheet.write(row, 22, "/", label_small_fmt)  # W6
        sheet.write(row, 26, "เก็บเช็ค", label_small_fmt)  # AA6
        row += 1

        # ================= Row 7-9: Company Info Box + Schedule Box =================
        # Company box: A7:W9
        sheet.merge_range(row, 0, row + 2, 22,
            "ถึง    บริษัท อิออน(ไทยแลนด์) จำกัด สาขาที่ สำนักงานใหญ่  Tax ID 0105527044125\n"
            "       78 อาคารอิออนหลักสี่ ชั้น 2 ถ.แจ้งวัฒนะ แขวงอนุสาวรีย์ เขตบางเขน กทม.10220\n"
            "       โทร 02-970-1825-30  ต่อ 233, 235 ,236  แฟกซ์ 02-970-1823-4",
            company_box_no_bottom_fmt
        )
        
        # Schedule box top: X7:AD8
        sheet.merge_range(row, 23, row + 1, 29,
            "งวด/วันที่ครบกำหนด ...../...../.....  ",
            bottom_align_no_border_fmt
        )
        sheet.set_row(row, 13.8)
        row += 2
        
        # Row 9: Bottom part of boxes
        sheet.merge_range(row, 23, row, 24, "ผู้วางบิล", bottom_align_small_no_border_fmt)  # X9:Y9
        sheet.merge_range(row, 25, row, 26, "", bottom_align_small_no_border_fmt)  # Z9:AA9
        sheet.write(row, 27, "วันที่", bottom_align_small_no_border_fmt)  # AB9 - single cell!
        sheet.merge_range(row, 28, row, 29, "", workbook.add_format({
            "font_size": 8,
            "valign": "bottom",
            "right": 1
        }))  # AC9:AD9 - empty
        row += 1

        # ================= Row 10: Rebate note =================
        sheet.merge_range(row, 0, row, 22, "(Rebate……%Dc……%)ใส่รีเบท. ดีซี", rebate_note_border_fmt)  # A10:W10 - align RIGHT!
        sheet.merge_range(row, 23, row, 24, "", left_bottom_border_fmt)  # X10:Y10 empty
        sheet.merge_range(row, 25, row, 28, "สำหรับ-เจ้าหน้าที่อิออนฯ", bottom_align_bottom_border_fmt)  # Z10:AC10 - center
        sheet.write(row, 29, "", right_bottom_border_fmt) # AD10 - empty
        sheet.set_row(row, 13.8)
        row += 1

        # ================= Row 11-12: Table Headers =================
        # Row 11: Main headers (merged with row 12 for most columns)
        sheet.merge_range(row, 0, row + 1, 1, "รหัส\nสาขา", header_fmt)
        sheet.merge_range(row, 2, row + 1, 7, "ชื่อ\nสาขา", header_fmt)
        sheet.merge_range(row, 8, row + 1, 9, "จำนวนบิล\nรวม", header_fmt)
        sheet.merge_range(row, 10, row + 1, 13, "จำนวนเงินรวม\nแต่ละสาขา", header_fmt)
        sheet.merge_range(row, 14, row + 1, 17, "หักเงินรับคืนสินค้า\nหรือส่วนลด (ถ้ามี)", header_fmt)
        sheet.merge_range(row, 18, row + 1, 22, "จำนวนเงินคงเหลือสุทธิ", header_fmt)
        sheet.merge_range(row, 24, row, 27, "Payment Amount", header_gray_no_bottom_fmt_payment)
        sheet.merge_range(row, 28, row, 29, "Checked", header_gray_no_bottom_fmt_checked)  # AC11:AD11 - NOT merged with row 12!
        
        sheet.set_row(row, 15)  # Set row 11 height to 15
        row += 1
        
        # Row 12: Sub-header for Payment Amount and separate Checked
        sheet.merge_range(row, 24, row, 27, "(Supp's R/B…...%)", sub_header_fmt)
        sheet.merge_range(row, 28, row, 29, "", sub_header_fmt)  # AC12:AD12 - separate from row 11
        sheet.set_row(row, 19.95)
        row += 1
        
        data_start_row = row

        # ================= Data Rows (13-21: 9 rows) =================
        for i in range(9):
            sheet.merge_range(row, 0, row, 1, "", cell_center_fmt)
            sheet.merge_range(row, 2, row, 7, "", cell_left_fmt)
            sheet.merge_range(row, 8, row, 9, "", cell_center_fmt)
            sheet.merge_range(row, 10, row, 13, "", cell_right_fmt)
            sheet.merge_range(row, 14, row, 17, "", cell_right_fmt)
            sheet.merge_range(row, 18, row, 22, "", cell_right_fmt)
            sheet.merge_range(row, 24, row, 27, "", cell_right_fmt)
            sheet.merge_range(row, 28, row, 29, "", cell_center_fmt)
            sheet.set_row(row, 19.95)
            row += 1
            
        data_end_row = row - 1

        # ================= Summary Row (22) =================
        sheet.merge_range(row, 0, row, 1, "", summary_label_fmt)  # A22:B22
        sheet.merge_range(row, 2, row, 7, "จำนวนบิล/จำนวนเงินรวม", summary_label_fmt)  # C22:H22
        sheet.merge_range(row, 8, row, 9, "", summary_value_fmt)  # I22:J22 จำนวนบิลรวม
        sheet.write_formula(
            row,
            8,
            f"=SUM(I{data_start_row+1}:I{data_end_row+1})",
            summary_int_fmt
        )
        sheet.merge_range(row, 10, row, 13, "", summary_value_fmt)  # K22:N22 จำนวนเงินรวมแต่ละสาขา
        sheet.write_formula(
            row,
            10,
            f"=SUM(K{data_start_row+1}:K{data_end_row+1})",
            summary_value_fmt
        )
        sheet.merge_range(row, 14, row, 17, "", summary_value_fmt)  # O22:R22 หักเงินรับคืนสินค้าหรือส่วนลด
        sheet.write_formula(
            row,
            14,
            f"=SUM(O{data_start_row+1}:O{data_end_row+1})",
            summary_value_fmt
        )
        sheet.merge_range(row, 18, row, 22, "", summary_value_fmt)  # S22:W22 จำนวนเงินคงเหลือสุทธิ
        sheet.write_formula(
            row,
            18,
            f"=SUM(S{data_start_row+1}:S{data_end_row+1})",
            summary_value_fmt
        )
        # No X22 - column X (index 23) has no cell
        sheet.merge_range(row, 24, row, 27, "", summary_value_fmt)  # Y22:AB22
        sheet.merge_range(row, 28, row, 29, "", summary_value_fmt)  # AC22:AD22
        sheet.set_row(row, 19.95)
        row += 1
        
        # ================= Row 23: Additional summary cells =================
        sheet.merge_range(row, 24, row, 27, "", summary_value_fmt)  # Y23:AB23
        sheet.merge_range(row, 28, row, 29, "", summary_value_fmt)  # AC23:AD23
        sheet.set_row(row, 19.95)
        row += 2

        # ================= Footer: Instructions (Row 25) =================
        sheet.merge_range(row, 2, row, 5, "เอกสารที่ใช้ในการวางบิล", footer_title_fmt)  # C25:F25
        sheet.merge_range(row, 18, row, 22, "กำหนดการวางบิลและรับเช็ค", footer_title_fmt)  # S25:W25
        sheet.set_row(row, 13.8)
        row += 1
        
        # Row 26
        # A26 standalone or merged? Based on data, seems standalone
        sheet.write(row, 0,
            "ในนามบริษัทจำกัด, ห้างหุ้นส่วนจำกัด, บุคคล (ในระบบภาษี vat และนอกระบบภาษี-ไม่มี vat)",
            footer_subtitle_fmt
        )
        # S26:AD28 merged (3 rows!)
        sheet.merge_range(row, 18, row + 2, 29,
            "บจก.อิออนฯรับวางบิลเวลา 10.00 - 17.00 น.\n"
            "รับวางบิลวันที่ ตามที่อิออนฯประกาศให้ทราบ\n"
            "กรณีรับเช็ค รับที่ฝ่ายบัญชี-สนญ(ใช้เอกสารนี้และถ่ายสำเนาบัตรประชาชน)\n"
            "รับเช็คอิออนฯ ตามวันที่ชำระเงิน เวลา 10.00-16.00น.",
            footer_text_fmt
        )
        sheet.set_row(row, 13.8)
        row += 1

        # Instruction 1 (Row 27-28: 2 rows)
        sheet.write(row, 0, "1", footer_number_fmt)
        sheet.merge_range(row, 1, row + 1, 15,
            "ต้นฉบับใบเสร็จหรือบิลเงินสด ที่มีตราประทับและเซ็นรับสินค้า **\n"
            "ถ้าเอกสารข้อ 1 ไม่ตรงตามเงื่อนไข ให้เพิ่มสำเนาอินวอยน์ที่มีตราประทับฯ 1 ใบต่อ 1 อินวอยน์",
            footer_text_fmt
        )  # B27:P28
        sheet.set_row(row, 13.8)
        row += 1
        sheet.set_row(row, 13.8)
        row += 1
        
        # Instruction 2 (Row 29)
        sheet.write(row, 0, "2", footer_number_fmt)
        sheet.merge_range(row, 1, row, 15,
            "ใบพีโอสีขาวขนาดครึ่ง A4 ใช้เฉพาะดีซีบางเสาธง 0081,0082 ต้องมีตราประทับและชื่อผู้รับสินค้า",
            footer_text_fmt_vcenter
        )  # B29:P29
        sheet.set_row(row, 13.8)
        row += 1
        
        # Instruction 3 (Row 30)
        sheet.write(row, 0, "3", footer_number_fmt)
        sheet.merge_range(row, 1, row, 16,
            "สำเนาใบลดหนี้(ถ้ามี)...สินค้าฝากขาย ใช้ยอดขาย+ใบเสร็จ+สำเนาอินวอยน์-สำเนาลดหนี้ที่มีตราประทับฯ",
            footer_text_fmt_vcenter
        )  # B30:P30
        sheet.set_row(row, 13.8)
        row += 1
        
        # Instruction - หมายเหตุ (Row 31)
        sheet.merge_range(row, 0, row, 1, "หมายเหตุ :", footer_title_fmt)  # A31:B31
        sheet.merge_range(row, 2, row, 22,
            "ใบพีโอจากดีซีต้องมีตราประทับรับสินค้า, อินวอยน์ต้องมีผู้รับสินค้า+ตราประทับยาง และต้องระบุเลขที่พีโอของอิออนฯ",
            footer_text_fmt_vcenter
        )  # C31:T31
        sheet.set_row(row, 13.8)
        row += 1

        # Final note 1 (Row 32)
        sheet.merge_range(row, 0, row, 22,
            "เอกสารฉบับนี้ ใช้สำหรับวางบิลเบื้องต้นเท่านั้น บจก.อิออนฯจะตรวจสอบเอกสารและเงื่อนไขการชำระเงินภายหลัง -หากวันนัดไม่ถูกต้องขอให้รีบแจ้งทันที",
            footer_text_fmt_vcenter
        )  # A32:U32
        sheet.set_row(row, 13.8)
        row += 1
        
        # Final note 2 (Row 33)
        sheet.merge_range(row, 0, row, 21,
            "เอกสารฉบับนี้ใช้แสดงการสรุปการส่งเอกสารวางบิลเท่านั้น ไม่สามารถให้บุคคลอื่นใช้สิทธิเรียกร้องหรือรับช่วงสิทธิเรียกร้องใดๆแก่บริษัทได้",
            footer_bold_fmt
        )  # A33:V33
        sheet.set_row(row, 13.8)
        row += 1
        
        # Contact info (Row 34)
        sheet.merge_range(row, 0, row, 8,
            "ฝ่ายบัญชี เจ้าหนี้การค้าโทร. 02-970-1825 ต่อ 233, 235, 236",
            footer_small_fmt
        )  # A34:I34
        sheet.merge_range(row, 17, row, 21, "Update A/P trade", footer_small_fmt)  # R34:U34