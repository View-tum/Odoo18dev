# purchase_order_status_report/report/purchase_order_status_xlsx.py
from odoo import models


class PurchaseOrderStatusXlsx(models.AbstractModel):
    _name = "report.purchase_order_status_report.po_status_report_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "Purchase Order Status XLSX Report"

    def generate_xlsx_report(self, workbook, data, wizard):
        wizard = self.env["purchase.order.status.report.wizard"].browse(
            data.get("wizard_id")
        )

        # reuse QWeb provider
        qweb_report = self.env["report.purchase_order_status_report.po_status_report"]
        report_values = qweb_report._get_report_values([], data=data)
        lines = report_values.get("lines", [])
        filters = report_values.get("filters", {})
        company = report_values.get("company")

        sheet = workbook.add_worksheet("PO Status")

        # --------- Formats ---------
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

        date_center_fmt = workbook.add_format({
            "border": 1,
            "align": "center",
            "valign": "vcenter",
            "font_size": 10,
            "num_format": "yyyy-mm-dd",
        })

        num_fmt = workbook.add_format(
            {
                "border": 1,
                "align": "right",
                "valign": "vcenter",
                "num_format": "#,##0.00",
                "font_size": 10,
            }
        )

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
            "sent": workbook.add_format(
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
            "to approve": workbook.add_format(
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
            "purchase": workbook.add_format(
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

        billing_formats = {
            "no": workbook.add_format(
                {
                    "border": 1,
                    "align": "center",
                    "valign": "vcenter",
                    "fg_color": "#95a5a6",
                    "font_color": "white",
                    "font_size": 10,
                    "bold": True,
                }
            ),
            "to invoice": workbook.add_format(
                {
                    "border": 1,
                    "align": "center",
                    "valign": "vcenter",
                    "fg_color": "#3498db",
                    "font_color": "white",
                    "font_size": 10,
                    "bold": True,
                }
            ),
            "invoiced": workbook.add_format(
                {
                    "border": 1,
                    "align": "center",
                    "valign": "vcenter",
                    "fg_color": "#27ae60",
                    "font_color": "white",
                    "font_size": 10,
                    "bold": True,
                }
            ),
        }

        status_display = {
            "draft": "ใบขอเสนอราคา",
            "sent": "ส่งใบขอเสนอราคาแล้ว",
            "to approve": "รออนุมัติ",
            "purchase": "ใบสั่งซื้อ",
            "done": "ล็อกแล้ว",
            "rejected": "ปฏิเสธ",
            "cancel": "ยกเลิก",
        }

        billing_display = {
            "no": "ยังไม่ต้องวางบิล",
            "to invoice": "รอวางบิล",
            "invoiced": "วางบิลครบแล้ว",
        }

        # --------- Header ---------
        row = 0
        sheet.merge_range(row, 0, row, 11, "รายงานสถานะใบสั่งซื้อ", title_fmt)
        sheet.set_row(row, 25)
        row += 2

        sheet.write(row, 0, "บริษัท:", filter_label_fmt)
        sheet.merge_range(row, 1, row, 3, company.name or "", filter_value_fmt)
        sheet.write(row, 4, "ช่วงวันที่:", filter_label_fmt)
        sheet.merge_range(
            row,
            5,
            row,
            8,
            f"{filters.get('date_from','')} - {filters.get('date_to','')}",
            filter_value_fmt,
        )
        row += 1

        vendor_name = filters.get("vendor").name if filters.get("vendor") else "ทั้งหมด"
        product_name = (
            filters.get("product").display_name if filters.get("product") else "ทั้งหมด"
        )

        sheet.write(row, 0, "ผู้ขาย:", filter_label_fmt)
        sheet.merge_range(row, 1, row, 3, vendor_name, filter_value_fmt)
        sheet.write(row, 4, "สินค้า:", filter_label_fmt)
        sheet.merge_range(row, 5, row, 8, product_name, filter_value_fmt)
        row += 1

        status_filter = (
            status_display.get(filters.get("state"), "ทั้งหมด")
            if filters.get("state")
            else "ทั้งหมด"
        )
        billing_filter = (
            billing_display.get(filters.get("invoice_status"), "ทั้งหมด")
            if filters.get("invoice_status")
            else "ทั้งหมด"
        )

        sheet.write(row, 0, "สถานะใบสั่งซื้อ:", filter_label_fmt)
        sheet.merge_range(row, 1, row, 3, status_filter, filter_value_fmt)
        sheet.write(row, 4, "สถานะการวางบิล:", filter_label_fmt)
        sheet.merge_range(row, 5, row, 8, billing_filter, filter_value_fmt)
        row += 2

        # --------- Column headers (สลับให้ Status มาก่อน Billing) ---------
        headers = [
            "เลขที่ใบสั่งซื้อ",
            "อ้างอิง",
            "วันที่สั่งซื้อ",
            "วันที่คาดว่าจะมาถึง",
            "ผู้ขาย",
            "สินค้า",
            "จำนวน",
            "หน่วยนับ",
            "ราคาต่อหน่วย",
            "ยอดไม่รวมภาษี",
            "สถานะใบสั่งซื้อ",          # ⬅ Order Status
            "สถานะการวางบิล",  # ⬅ Billing Status
        ]
        for col, header in enumerate(headers):
            sheet.write(row, col, header, header_fmt)
        sheet.set_row(row, 30)
        row += 1

        # --------- Data lines (เขียน Status ก่อน Billing) ---------
        for line in lines:
            col = 0

            sheet.write(row, col, line.get("order_name", ""), text_fmt)
            col += 1
            sheet.write(row, col, line.get("source_document", ""), text_fmt)
            col += 1
            od_date = line.get("order_date")
            sheet.write(row, col, od_date or "", date_center_fmt)
            col += 1
            ept_date = line.get("expected_arrival")
            sheet.write(row, col, ept_date or "", date_center_fmt)
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
            sheet.write(row, col, line.get("unit_price", 0.0), num_fmt)
            col += 1
            sheet.write(row, col, line.get("subtotal", 0.0), num_fmt)
            col += 1

            # Order Status
            st = line.get("state")
            st_text = status_display.get(st, st or "")
            st_fmt = status_formats.get(st, text_center_fmt)
            sheet.write(row, col, st_text, st_fmt)
            col += 1

            # Billing Status
            inv_state = line.get("invoice_status")
            inv_text = billing_display.get(inv_state, inv_state or "")
            inv_fmt = billing_formats.get(inv_state, text_center_fmt)
            sheet.write(row, col, inv_text, inv_fmt)

            sheet.set_row(row, 20)
            row += 1

        # --------- Summary ---------
        row += 1
        sheet.merge_range(
            row,
            0,
            row,
            10,  # ปล่อยคอลัมน์สุดท้ายว่างไว้เหมือนเดิม
            f"จํานวนรายการทั้งหมด: {len(lines)}",
            filter_label_fmt,
        )

        # --------- Column widths & freeze ---------
        sheet.set_column(0, 0, 15)    # PO Number
        sheet.set_column(1, 1, 18)    # Source Document
        sheet.set_column(2, 3, 14)    # Dates
        sheet.set_column(4, 4, 25)    # Vendor
        sheet.set_column(5, 5, 40)    # Product
        sheet.set_column(6, 7, 10)    # Qty, UoM
        sheet.set_column(8, 9, 15)    # Unit Price, Subtotal
        sheet.set_column(10, 11, 18)  # Status, Billing

        # header row อยู่แถว index 6 -> freeze หลัง header
        sheet.freeze_panes(7, 0)
