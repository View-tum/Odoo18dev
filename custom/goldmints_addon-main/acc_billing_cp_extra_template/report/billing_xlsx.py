from odoo import models


class BillingCpExtraXlsx(models.AbstractModel):
    _name = "report.acc_billing_cp_extra_template.billing_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "CP Extra Billing XLSX"

    def generate_xlsx_report(self, workbook, data, bills):
        sheet = workbook.add_worksheet("CP Extra Billing")

        # ================= Formats =================
        title_fmt = workbook.add_format({
            "font_size": 13,
            "bold": True,
            "align": "center",
            "valign": "vcenter",
            "text_wrap": True
        })
        
        company_info_fmt = workbook.add_format({
            "font_size": 13,
            "bold": True,
            "align": "center",
            "valign": "vcenter",
            "text_wrap": True
        })
        
        label_fmt = workbook.add_format({
            "font_size": 11,
            "align": "left",
            "valign": "vcenter"
        })
        
        info_fmt = workbook.add_format({
            "font_size": 11,
            "align": "left",
            "valign": "vcenter"
        })
        
        header_fmt = workbook.add_format({
            "font_size": 11,
            "bold": True,
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
            "left_color": "#000000",
            "right": 1,
            "right_color": "#000000",
            "bottom": 1,
            "bottom_color": "#D3D3D3"
        })
        
        cell_left_fmt = workbook.add_format({
            "font_size": 11,
            "align": "left",
            "valign": "vcenter",
            "left": 1,
            "left_color": "#000000",
            "right": 1,
            "right_color": "#000000",
            "bottom": 1,
            "bottom_color": "#D3D3D3"
        })
        
        cell_right_fmt = workbook.add_format({
            "font_size": 11,
            "align": "right",
            "valign": "vcenter",
            "left": 1,
            "left_color": "#000000",
            "right": 1,
            "right_color": "#000000",
            "bottom": 1,
            "bottom_color": "#D3D3D3"
        })
        
        summary_label_fmt = workbook.add_format({
            "font_size": 11,
            "align": "right",
            "valign": "vcenter",
            "top": 1,
            "top_color": "#000000"
        })
        
        summary_amount_fmt = workbook.add_format({
            "font_size": 11,
            "bold": True,
            "align": "right",
            "valign": "vcenter",
            "num_format": "#,##0.00",
            "top": 1,
            "top_color": "#000000",
            "bottom": 6,  # Double bottom border
            "bottom_color": "#000000"
        })
        
        signature_label_fmt = workbook.add_format({
            "font_size": 11,
            "align": "left",
            "valign": "vcenter"
        })
        
        signature_line_fmt = workbook.add_format({
            "font_size": 11,
            "align": "left",
            "valign": "bottom"
        })

        # ================= Column Width =================
        sheet.set_column("A:A", 9)    # ลำดับที่
        sheet.set_column("B:B", 18)   # เลขที่ใบแจ้งหนี้
        sheet.set_column("C:C", 20)   # เลขที่หนังสือรับรอง
        sheet.set_column("D:D", 17)   # วันที่หัก ณ ที่จ่าย
        sheet.set_column("E:E", 18)   # จำนวนเงินตามใบแจ้งหนี้
        sheet.set_column("F:F", 16)   # อัตราภาษีหัก
        sheet.set_column("G:G", 16)   # ยอดภาษีหัก

        row = 0

        # ================= Header Title =================
        sheet.merge_range(row, 0, row, 6,
            "ใบวางบิล ภาษีหัก ณ ที่จ่าย",
            title_fmt
        )
        row += 1

        # ================= Company Info =================
        sheet.merge_range(row, 0, row, 6,
            "บริษัท ซีพี แอ็กซ์ตร้า จำกัด (มหาชน) สาขา 00175",
            company_info_fmt
        )
        row += 1
        
        sheet.merge_range(row, 0, row, 6,
            "629/1 ถนนนวมินทร์ แขวงคลองกุ่ม เขตบึงกุ่ม กรุงเทพฯ 10230",
            company_info_fmt
        )
        row += 2

        # ================= Partner Info =================
        # Row 1: รหัสลูกค้า and เลขประจำตัวผู้เสียภาษี
        sheet.write(row, 0, "รหัสลูกค้า", label_fmt)
        sheet.merge_range(row, 1, row, 2, "2505", info_fmt)
        sheet.write(row, 3, "เลขประจำตัวผู้เสียภาษี", label_fmt)
        sheet.merge_range(row, 4, row, 5, "0105532084750", info_fmt)
        row += 1
        
        # Row 2: ชื่อบริษัท
        sheet.write(row, 0, "ชื่อบริษัท", label_fmt)
        sheet.merge_range(row, 1, row, 6, "บริษัท โกลด์ มิ้นท์ โปรดักส์ จำกัด", info_fmt)
        row += 1
        
        # Row 3: ที่อยู่บริษัท
        sheet.write(row, 0, "ที่อยู่บริษัท", label_fmt)
        sheet.merge_range(row, 1, row, 6, "248/1 ซ.โสภณ ถ.เลียบทางด่วน แขวงบางนาเหนือ เขตบางนา กทม. 10260", info_fmt)
        row += 1
        
        # Row 4: ชื่อผู้ติดต่อ and โทร.
        sheet.write(row, 0, "ชื่อผู้ติดต่อ :", label_fmt)
        sheet.merge_range(row, 1, row, 2, "นิธิดา", info_fmt)
        sheet.write(row, 3, "โทร.", label_fmt)
        sheet.merge_range(row, 4, row, 5, "02-744-8497-8", info_fmt)
        row += 2

        # ================= Table Header =================
        sheet.write(row, 0, "ลำดับที่", header_fmt)
        sheet.write(row, 1, "เลขที่ใบแจ้งหนี้", header_fmt)
        sheet.write(row, 2, "เลขที่หนังสือรับรอง\nการหัก ณ ที่จ่าย", header_fmt)
        sheet.write(row, 3, "วันที่หัก ณ ที่จ่าย", header_fmt)
        sheet.write(row, 4, "จำนวนเงินตาม\nใบแจ้งหนี้", header_fmt)
        sheet.write(row, 5, "อัตราภาษีหัก\nณ ที่จ่าย", header_fmt)
        sheet.write(row, 6, "ยอดภาษีหัก ณ\nที่จ่าย", header_fmt)
        
        sheet.set_row(row, 45)  # Set header row height to 45
        row += 1
        
        data_start_row = row

        # ================= Data Rows (10 empty rows) =================
        for i in range(10):
            sheet.write(row, 0, "", cell_center_fmt)
            sheet.write(row, 1, "", cell_left_fmt)
            sheet.write(row, 2, "", cell_left_fmt)
            sheet.write(row, 3, "", cell_center_fmt)
            sheet.write(row, 4, "", cell_right_fmt)
            sheet.write(row, 5, "", cell_center_fmt)
            sheet.write(row, 6, "", cell_right_fmt)
            sheet.set_row(row, 25)  # Set data row height to 25
            row += 1
            
        data_end_row = row - 1

        # ================= Summary Row =================
        sheet.merge_range(row, 0, row, 5, "รวมเป็นจำนวนเงินทั้งสิ้น", summary_label_fmt)
        sheet.write_formula(
            row,
            6,
            f"=SUM(G{data_start_row+1}:G{data_end_row+1})",
            summary_amount_fmt
        )
        sheet.set_row(row, 25)  # Set summary row height to 25
        row += 2

        # ================= Footer Signature =================
        sheet.write(row, 3, "ผู้รับวางบิล", signature_label_fmt)
        sheet.merge_range(row, 4, row, 6,
            "............................................................................",
            signature_line_fmt
        )
        row += 1
        
        sheet.write(row, 3, "ลงวันที่", signature_label_fmt)
        sheet.merge_range(row, 4, row, 6,
            "............................................................................",
            signature_line_fmt
        )