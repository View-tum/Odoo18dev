# purchase_request_status_report/report/purchase_request_status_xlsx.py
from odoo import models


class PurchaseRequestStatusXlsx(models.AbstractModel):
    _name = "report.purchase_request_status_report.pr_status_report_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "Purchase Request Status XLSX Report"

    def generate_xlsx_report(self, workbook, data, wizard):
        wizard = self.env["purchase.request.status.report.wizard"].browse(
            data.get("wizard_id")
        )

        # reuse logic จาก QWeb provider
        qweb_report = self.env["report.purchase_request_status_report.pr_status_report"]
        report_values = qweb_report._get_report_values([], data=data)
        lines = report_values.get("lines", [])
        filters = report_values.get("filters", {})
        company = report_values.get("company")

        sheet = workbook.add_worksheet("PR Status")

        # ========== Define Formats ==========

        # Title format
        title_fmt = workbook.add_format(
            {
                "bold": True,
                "font_size": 16,
                "align": "center",
                "valign": "vcenter",
                "fg_color": "#2c3e50",
                "font_color": "white",
                "border": 1,
            }
        )

        # Filter info formats
        filter_label_fmt = workbook.add_format(
            {
                "bold": True,
                "font_size": 10,
                "fg_color": "#ecf0f1",
                "border": 1,
                "valign": "vcenter",
            }
        )

        filter_value_fmt = workbook.add_format(
            {
                "font_size": 10,
                "border": 1,
                "valign": "vcenter",
            }
        )

        # Header format
        header_fmt = workbook.add_format(
            {
                "bold": True,
                "font_size": 11,
                "align": "center",
                "valign": "vcenter",
                "fg_color": "#34495e",
                "font_color": "white",
                "border": 1,
                "text_wrap": True,
            }
        )

        # Data formats
        text_fmt = workbook.add_format(
            {
                "border": 1,
                "valign": "vcenter",
                "font_size": 10,
            }
        )

        text_center_fmt = workbook.add_format(
            {
                "border": 1,
                "align": "center",
                "valign": "vcenter",
                "font_size": 10,
            }
        )

        date_center_fmt = workbook.add_format(
            {
                "border": 1,
                "align": "center",
                "valign": "vcenter",
                "font_size": 10,
                "num_format": "yyyy-mm-dd",
            }
        )

        num_fmt = workbook.add_format(
            {
                "border": 1,
                "align": "right",
                "valign": "vcenter",
                "num_format": "#,##0.00",
                "font_size": 10,
            }
        )

        # Status formats with colors
        status_formats = {
            "draft": workbook.add_format(
                {
                    "border": 1,
                    "align": "center",
                    "valign": "vcenter",
                    "bold": True,
                    "fg_color": "#95a5a6",
                    "font_color": "white",
                    "font_size": 10,
                }
            ),
            "pr_approval_lvl1": workbook.add_format(
                {
                    "border": 1,
                    "align": "center",
                    "valign": "vcenter",
                    "bold": True,
                    "fg_color": "#f39c12",
                    "font_color": "white",
                    "font_size": 10,
                }
            ),
            "pr_approval_lvl2": workbook.add_format(
                {
                    "border": 1,
                    "align": "center",
                    "valign": "vcenter",
                    "bold": True,
                    "fg_color": "#e67e22",
                    "font_color": "white",
                    "font_size": 10,
                }
            ),
            "approved": workbook.add_format(
                {
                    "border": 1,
                    "align": "center",
                    "valign": "vcenter",
                    "bold": True,
                    "fg_color": "#27ae60",
                    "font_color": "white",
                    "font_size": 10,
                }
            ),
            "in_progress": workbook.add_format(
                {
                    "border": 1,
                    "align": "center",
                    "valign": "vcenter",
                    "bold": True,
                    "fg_color": "#3498db",
                    "font_color": "white",
                    "font_size": 10,
                }
            ),
            "done": workbook.add_format(
                {
                    "border": 1,
                    "align": "center",
                    "valign": "vcenter",
                    "bold": True,
                    "fg_color": "#16a085",
                    "font_color": "white",
                    "font_size": 10,
                }
            ),
            "rejected": workbook.add_format(
                {
                    "border": 1,
                    "align": "center",
                    "valign": "vcenter",
                    "bold": True,
                    "fg_color": "#e74c3c",
                    "font_color": "white",
                    "font_size": 10,
                }
            ),
            "cancel": workbook.add_format(
                {
                    "border": 1,
                    "align": "center",
                    "valign": "vcenter",
                    "bold": True,
                    "fg_color": "#7f8c8d",
                    "font_color": "white",
                    "font_size": 10,
                }
            ),
        }

        # ========== Write Report ==========

        row = 0

        # Title (merged across all columns)
        sheet.merge_range(row, 0, row, 7, "รายงานสถานะใบขอซื้อ", title_fmt)
        sheet.set_row(row, 25)  # Set row height
        row += 1

        # Empty row
        row += 1

        # Filter Information Section
        status_display = {
            "draft": "ใบขอเสนอราคา",
            "pr_approval_lvl1": "อนุมัติใบขอซื้อ ระดับ 1",
            "pr_approval_lvl2": "อนุมัติใบขอซื้อ ระดับ 2",
            "approved": "อนุมัติ",
            "in_progress": "กำลังดำเนินการ",
            "done": "เสร็จสิ้น",
            "rejected": "ปฏิเสธ",
            "cancel": "ยกเลิก",
        }

        # Company
        sheet.write(row, 0, "บริษัท:", filter_label_fmt)
        sheet.merge_range(row, 1, row, 3, company.name or "", filter_value_fmt)
        sheet.write(row, 4, "ช่วงวันที่:", filter_label_fmt)
        sheet.merge_range(
            row,
            5,
            row,
            7,
            f"{filters.get('date_from', '')} - {filters.get('date_to', '')}",
            filter_value_fmt,
        )
        row += 1

        # Vendor
        sheet.write(row, 0, "ผู้ขาย:", filter_label_fmt)
        vendor_name = filters.get("vendor").name if filters.get("vendor") else "ทั้งหมด"
        sheet.merge_range(row, 1, row, 3, vendor_name, filter_value_fmt)
        sheet.write(row, 4, "สินค้า:", filter_label_fmt)
        product_name = (
            filters.get("product").display_name if filters.get("product") else "ทั้งหมด"
        )
        sheet.merge_range(row, 5, row, 7, product_name, filter_value_fmt)
        row += 1

        # Status Filter
        sheet.write(row, 0, "สถานะ:", filter_label_fmt)
        status_filter = (
            status_display.get(filters.get("state"), "ทั้งหมด")
            if filters.get("state")
            else "ทั้งหมด"
        )
        sheet.merge_range(row, 1, row, 3, status_filter, filter_value_fmt)
        row += 1

        # Empty row
        row += 1

        # Column Headers
        headers = [
            "เลขที่ใบขอซื้อ",
            "วันที่ขอซื้อ",
            "ผู้ขาย",
            "สินค้า",
            "จำนวน",
            "หน่วยนับ",
            "ต้นทุนประมาณการ",
            "สถานะ",
        ]

        for col, header in enumerate(headers):
            sheet.write(row, col, header, header_fmt)

        sheet.set_row(row, 30)
        row += 1

        # Data Lines
        for line in lines:
            req = line["request"]
            ln = line.get("line")

            col = 0
            sheet.write(row, col, line.get("request_name", ""), text_fmt)
            col += 1
            req_date = line.get("request_date")
            sheet.write(row, col, req_date or "", date_center_fmt)
            col += 1
            sheet.write(
                row,
                col,
                line.get("vendor").name if line.get("vendor") else "",
                text_fmt,
            )
            col += 1
            sheet.write(
                row,
                col,
                line.get("product").display_name if line.get("product") else "",
                text_fmt,
            )
            col += 1
            sheet.write(row, col, line.get("qty", 0.0), num_fmt)
            col += 1
            sheet.write(
                row,
                col,
                line.get("uom").name if line.get("uom") else "",
                text_center_fmt,
            )
            col += 1
            sheet.write(row, col, line.get("estimated_cost", 0.0), num_fmt)
            col += 1

            # Status with color
            state = line.get("state", "draft")
            status_text = status_display.get(state, state)
            status_fmt = status_formats.get(state, text_center_fmt)
            sheet.write(row, col, status_text, status_fmt)

            sheet.set_row(row, 20)  # Set data row height
            row += 1

        # Empty row before summary
        row += 1

        # Summary row
        sheet.merge_range(
            row, 0, row, 7, f"จำนวนรายการทั้งหมด: {len(lines)}", filter_label_fmt
        )

        # ========== Column Widths ==========
        sheet.set_column(0, 0, 12)  # PR Number
        sheet.set_column(1, 1, 14)  # Request Date
        sheet.set_column(2, 2, 25)  # Vendor
        sheet.set_column(3, 3, 40)  # Product
        sheet.set_column(4, 4, 10)  # Qty
        sheet.set_column(5, 5, 10)  # UoM
        sheet.set_column(6, 6, 15)  # Estimated Cost
        sheet.set_column(7, 7, 18)  # Status

        # Freeze panes (freeze header row)
        sheet.freeze_panes(7, 0)  # Freeze at row 7 (after headers)
