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
        
        # Header Row Format (Bold & Light Grey background)
        header_row_fmt = workbook.add_format({
            "bold": True,
            "border": 1,
            "valign": "vcenter",
            "font_size": 10,
            "fg_color": "#f8f9fa",
        })
        
        header_row_num_fmt = workbook.add_format({
            "bold": True,
            "border": 1,
            "align": "right",
            "valign": "vcenter",
            "num_format": "#,##0.00",
            "font_size": 10,
            "fg_color": "#f8f9fa",
        })

        header_row_date_fmt = workbook.add_format({
            "bold": True,
            "border": 1,
            "align": "center",
            "valign": "vcenter",
            "num_format": "yyyy-mm-dd",
            "font_size": 10,
            "fg_color": "#f8f9fa",
        })

        # Detail Row Format
        detail_row_fmt = workbook.add_format({
            "border": 1,
            "valign": "vcenter",
            "font_size": 10,
            "font_color": "#5f6368",
        })
        
        detail_row_num_fmt = workbook.add_format({
            "border": 1,
            "align": "right",
            "valign": "vcenter",
            "num_format": "#,##0.00",
            "font_size": 10,
            "font_color": "#5f6368",
        })
        
        detail_row_date_fmt = workbook.add_format({
            "border": 1,
            "align": "center",
            "valign": "vcenter",
            "num_format": "yyyy-mm-dd",
            "font_size": 10,
            "font_color": "#5f6368",
        })

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
        
        billing_note_formats = {
            "no": workbook.add_format({"border": 1, "align": "center", "valign": "vcenter", "fg_color": "#7f8c8d", "font_color": "white", "font_size": 10, "bold": True}),
            "draft": workbook.add_format({"border": 1, "align": "center", "valign": "vcenter", "fg_color": "#3498db", "font_color": "white", "font_size": 10, "bold": True}),
            "partial": workbook.add_format({"border": 1, "align": "center", "valign": "vcenter", "fg_color": "#e67e22", "font_color": "white", "font_size": 10, "bold": True}),
            "fully": workbook.add_format({"border": 1, "align": "center", "valign": "vcenter", "fg_color": "#27ae60", "font_color": "white", "font_size": 10, "bold": True}),
        }

        billing_formats = {
            "no": workbook.add_format({"border": 1, "align": "center", "valign": "vcenter", "fg_color": "#7f8c8d", "font_color": "white", "font_size": 10, "bold": True}),
            "to invoice": workbook.add_format({"border": 1, "align": "center", "valign": "vcenter", "fg_color": "#3498db", "font_color": "white", "font_size": 10, "bold": True}),
            "invoiced": workbook.add_format({"border": 1, "align": "center", "valign": "vcenter", "fg_color": "#27ae60", "font_color": "white", "font_size": 10, "bold": True}),
        }

        status_display = {
            "draft": "ใบขอเสนอราคา", "sent": "ส่งใบขอเสนอราคาแล้ว", "to approve": "รออนุมัติ",
            "purchase": "ใบสั่งซื้อ", "done": "ล็อกแล้ว", "rejected": "ปฏิเสธ", "cancel": "ยกเลิก",
        }

        billing_note_display = {
            "no": "ยังไม่วางบิล", "draft": "ร่างใบวางบิล", 
            "partial": "วางบิลบางส่วน", "fully": "วางบิลครบแล้ว",
        }

        billing_display = {
            "no": "ยังไม่ตั้งหนี้", "to invoice": "รอตั้งหนี้", "invoiced": "ตั้งหนี้ครบแล้ว",
        }

        # --------- Header ---------
        row = 0
        sheet.merge_range(row, 0, row, 18, "รายงานสถานะใบสั่งซื้อ", title_fmt) # ขยายเป็น 18
        sheet.set_row(row, 25)
        row += 2

        # ข้อมูลเงื่อนไขด้านบนเหมือนเดิม ... (บริษัท, ช่วงวันที่, ผู้ขาย, สินค้า)
        sheet.write(row, 0, "บริษัท:", filter_label_fmt)
        sheet.merge_range(row, 1, row, 3, company.name or "", filter_value_fmt)
        sheet.write(row, 4, "ช่วงวันที่:", filter_label_fmt)
        sheet.merge_range(row, 5, row, 8, f"{filters.get('date_from','')} - {filters.get('date_to','')}", filter_value_fmt)
        row += 1

        vendor_name = filters.get("vendor").name if filters.get("vendor") else "ทั้งหมด"
        product_name = filters.get("product").display_name if filters.get("product") else "ทั้งหมด"
        sheet.write(row, 0, "ผู้ขาย:", filter_label_fmt)
        sheet.merge_range(row, 1, row, 3, vendor_name, filter_value_fmt)
        sheet.write(row, 4, "สินค้า:", filter_label_fmt)
        sheet.merge_range(row, 5, row, 8, product_name, filter_value_fmt)
        row += 1

        status_filter = status_display.get(filters.get("state"), "ทั้งหมด") if filters.get("state") else "ทั้งหมด"
        bn_filter = billing_note_display.get(filters.get("billing_note_status"), "ทั้งหมด") if filters.get("billing_note_status") else "ทั้งหมด"
        billing_filter = billing_display.get(filters.get("invoice_status"), "ทั้งหมด") if filters.get("invoice_status") else "ทั้งหมด"

        sheet.write(row, 0, "สถานะใบสั่งซื้อ:", filter_label_fmt)
        sheet.merge_range(row, 1, row, 3, status_filter, filter_value_fmt)
        sheet.write(row, 4, "สถานะการวางบิล:", filter_label_fmt)
        sheet.merge_range(row, 5, row, 8, bn_filter, filter_value_fmt)
        row += 1
        
        sheet.write(row, 0, "สถานะการตั้งหนี้:", filter_label_fmt)
        sheet.merge_range(row, 1, row, 3, billing_filter, filter_value_fmt)
        row += 2

        # --------- Column headers ---------
        headers = [
            "เลขที่ใบสั่งซื้อ", "อ้างอิง", "ใบรับสินค้า/บริการ (SA/Receipt)", "วันที่รับของ", "เลขที่ใบแจ้งหนี้ (Inv Ref)", "วันที่สั่งซื้อ", "วันที่คาดว่าจะมาถึง",
            "ผู้ขาย", "สินค้า", "จำนวนสั่ง", "จำนวนรับ", "จำนวนค้างรับ", "จำนวนค้างตั้งหนี้",
            "หน่วยนับ", "ราคาต่อหน่วย", "ยอดไม่รวมภาษี", 
            "สถานะใบสั่งซื้อ", "สถานะการวางบิล", "สถานะการตั้งหนี้"
        ]
        for col, header in enumerate(headers):
            sheet.write(row, col, header, header_fmt)
        sheet.set_row(row, 30)
        row += 1

        # --------- Data lines ---------
        for line in lines:
            if line.get("is_header"):
                fmt_text = header_row_fmt
                fmt_num = header_row_num_fmt
                fmt_date = header_row_date_fmt
            else:
                fmt_text = detail_row_fmt
                fmt_num = detail_row_num_fmt
                fmt_date = detail_row_date_fmt
            
            col = 0
            
            # Identity Columns
            sheet.write(row, col, line.get("order_name", ""), fmt_text); col += 1
            sheet.write(row, col, line.get("source_document", ""), fmt_text); col += 1
            
            # Receipt Info
            sheet.write(row, col, line.get("receipt_ref", ""), fmt_text); col += 1
            sheet.write(row, col, line.get("receipt_date") or "", fmt_date); col += 1
            sheet.write(row, col, line.get("inv_ref", ""), fmt_text); col += 1
            
            # Dates & Vendor/Product
            sheet.write(row, col, line.get("order_date") or "", fmt_date); col += 1
            sheet.write(row, col, line.get("expected_arrival") or "", fmt_date); col += 1
            sheet.write(row, col, (line.get("vendor").name if line.get("vendor") else ""), fmt_text); col += 1
            sheet.write(row, col, line.get("product_display") or "", fmt_text); col += 1
            
            # Quantities
            sheet.write(row, col, line.get("qty", 0.0), fmt_num); col += 1
            sheet.write(row, col, line.get("qty_received", 0.0), fmt_num); col += 1
            sheet.write(row, col, line.get("qty_pending", 0.0), fmt_num); col += 1
            sheet.write(row, col, line.get("qty_pending_invoice", 0.0), fmt_num); col += 1
            
            # Financials
            sheet.write(row, col, (line.get("uom").name if line.get("uom") else ""), fmt_text); col += 1
            sheet.write(row, col, line.get("unit_price", 0.0), fmt_num); col += 1
            sheet.write(row, col, line.get("subtotal", 0.0), fmt_num); col += 1

            # Order Status
            st = line.get("state") or ""
            st_display = status_display.get(st, st)
            sheet.write(row, col, st_display, status_formats.get(st, fmt_text))
            col += 1
            
            # Billing Note Status
            bn_state = line.get("billing_note_status") or ""
            bn_display = billing_note_display.get(bn_state, bn_state)
            sheet.write(row, col, bn_display, billing_note_formats.get(bn_state, fmt_text))
            col += 1

            # Invoice Status
            inv_state = line.get("invoice_status") or ""
            inv_display = billing_display.get(inv_state, inv_state)
            sheet.write(row, col, inv_display, billing_formats.get(inv_state, fmt_text))

            sheet.set_row(row, 20)
            row += 1

        # --------- Summary ---------
        row += 1
        sheet.merge_range(row, 0, row, 18, f"จํานวนรายการทั้งหมด: {len(lines)}", filter_label_fmt)

        # --------- Column widths & freeze ---------
        sheet.set_column(0, 0, 15)    # PO Number
        sheet.set_column(1, 1, 15)    # Source Document
        sheet.set_column(2, 2, 25)    # Receipt / SA Ref
        sheet.set_column(3, 3, 15)    # Receipt Date
        sheet.set_column(4, 4, 20)    # Inv Ref
        sheet.set_column(5, 6, 14)    # Dates
        sheet.set_column(7, 7, 25)    # Vendor
        sheet.set_column(8, 8, 40)    # Product
        sheet.set_column(9, 12, 12)   # Qtys
        sheet.set_column(13, 13, 10)  # UoM
        sheet.set_column(14, 15, 15)  # Unit Price / Subtotal
        sheet.set_column(16, 18, 18)  # Statuses

        sheet.freeze_panes(8, 0)
