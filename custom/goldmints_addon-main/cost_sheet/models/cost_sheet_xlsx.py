# models/cost_sheet_xlsx.py
from odoo import models,fields, _


class CostSheetXlsx(models.AbstractModel):
    _name = "report.cost_sheet.report_cost_sheet_xlsx"
    _description = "Cost Sheet XLSX"
    _inherit = "report.report_xlsx.abstract"

    def _get_report_base_filename(self):
        self.ensure_one()
        lc_name = self.landed_cost_id.name or "cost_sheet"
        lc_name = lc_name.replace("/", "-")
        ts = fields.Datetime.now().strftime("%Y%m%d_%H%M%S")
        return "%s_%s" % (lc_name, ts)

    def generate_xlsx_report(self, workbook, data, wizards):
        """
        ใช้ data จาก QWeb (_get_report_values) เพื่อไม่ต้องเขียน logic ซ้ำ
        wizards = recordset ของ cost.sheet.wizard (ปกติ 1 record)
        """
        wizard = wizards[0]

        # reuse data จาก QWeb data provider
        qweb_report = self.env["report.cost_sheet.report_cost_sheet"]
        values = qweb_report._get_report_values(
            wizard.ids, data={"wizard_id": wizard.id}
        )
        payload = values.get("payload", {}) or {}
        sheets = payload.get("sheets", []) or []
        money = values.get("money")  # ฟังก์ชันจัดรูปแบบเงิน

        # === กำหนด format พื้นฐาน (แบบทางการ ไม่มีสี) ===
        title_fmt = workbook.add_format({
            "bold": True,
            "font_size": 16,
            "align": "center",
            "valign": "vcenter",
            "border": 1
        })
        
        header_label_fmt = workbook.add_format({
            "bold": True,
            "border": 1,
            "valign": "vcenter"
        })
        
        header_value_fmt = workbook.add_format({
            "border": 1,
            "valign": "vcenter",
            "text_wrap": True
        })
        
        header_table_fmt = workbook.add_format({
            "bold": True,
            "align": "center",
            "valign": "vcenter",
            "border": 1
        })
        
        normal_fmt = workbook.add_format({
            "border": 1,
            "valign": "vcenter"
        })
        
        num_fmt = workbook.add_format({
            "border": 1,
            "num_format": "#,##0.00",
            "align": "right",
            "valign": "vcenter"
        })
        
        qty_fmt = workbook.add_format({
            "border": 1,
            "num_format": "#,##0.00",
            "align": "right",
            "valign": "vcenter"
        })
        
        subtotal_label_fmt = workbook.add_format({
            "border": 1,
            "bold": True,
            "valign": "vcenter"
        })
        
        subtotal_value_fmt = workbook.add_format({
            "border": 1,
            "bold": True,
            "num_format": "#,##0.00",
            "align": "right",
            "valign": "vcenter"
        })
        
        section_header_fmt = workbook.add_format({
            "bold": True,
            "font_size": 12,
            "border": 1,
            "valign": "vcenter"
        })

        # วนทีละ sheet (1 landed cost ต่อ 1 worksheet)
        for idx, sheet in enumerate(sheets, start=1):
            ws_name = sheet.get("title") or _("Cost Sheet %s") % idx
            ws_name = ws_name[:31]  # Excel จำกัด 31 ตัวอักษร
            ws = workbook.add_worksheet(ws_name)

            # ตั้งค่าความกว้างคอลัมน์ - เริ่มจาก Column A
            start_col = 0  # เริ่มจาก Column A
            
            ws.set_column(start_col, start_col, 30)      # Column A - Labels/Product
            ws.set_column(start_col+1, start_col+1, 16)  # Column B - Amount/Quantity
            ws.set_column(start_col+2, start_col+2, 16)  # Column C - Additional Cost
            ws.set_column(start_col+3, start_col+3, 16)  # Column D - Final Cost
            ws.set_column(start_col+4, start_col+4, 16)  # Column E - Add. Cost/Unit
            ws.set_column(start_col+5, start_col+5, 16)  # Column F - Final Cost/Unit

            row = 0

            # ==== TITLE ====
            ws.merge_range(row, start_col, row, start_col+3, "COST SHEET", title_fmt)
            ws.set_row(row, 25)
            row += 2

            # ==== HEADER INFO ====
            def _w(label, value):
                nonlocal row
                if value:
                    ws.write(row, start_col, label, header_label_fmt)
                    ws.merge_range(row, start_col+1, row, start_col+3, value, header_value_fmt)
                    ws.set_row(row, 20)
                    row += 1

            _w("Company:", sheet.get("company") or "")
            _w("Period:", "%s - %s" % (sheet.get("date_from") or "", sheet.get("date_to") or ""))
            
            lc_title = sheet.get("title") or ""
            lc_date = sheet.get("lc_date") or ""
            if lc_title:
                if lc_date:
                    _w("Landed Cost:", "%s (%s)" % (lc_title, lc_date))
                else:
                    _w("Landed Cost:", lc_title)
            
            _w("Vendor:", sheet.get("vendor") or "")
            _w("Vendor Bill:", sheet.get("vendor_bill") or "")
            _w("Journal Entry:", sheet.get("journal_entry") or "")
            _w("Journal:", sheet.get("journal") or "")
            _w("Transfers:", sheet.get("pickings") or "")
            _w("Transfer Journal Entry:", sheet.get("transfer_journal_entry") or "")
            _w("Transfer Journal:", sheet.get("transfer_journal") or "")
            
            if sheet.get("description"):
                _w("Description:", sheet.get("description") or "")

            # เว้นบรรทัดก่อนตาราง
            row += 1

            # ==== ตาราง 1: Cost Components ====
            ws.merge_range(row, start_col, row, start_col+1, _("Cost Components"), section_header_fmt)
            ws.set_row(row, 22)
            row += 1

            ws.write(row, start_col, _("Item"), header_table_fmt)
            ws.write(row, start_col+1, _("Amount"), header_table_fmt)
            ws.set_row(row, 22)
            row += 1

            for line in sheet.get("lines", []) or []:
                ws.write(row, start_col, line.get("name") or "", normal_fmt)
                ws.write_number(
                    row,
                    start_col+1,
                    float(line.get("amount") or 0.0),
                    num_fmt,
                )
                ws.set_row(row, 20)
                row += 1

            # Summary rows
            # 1) Total Landed Cost
            ws.write(row, start_col, _("Total Landed Cost"), subtotal_label_fmt)
            ws.write_number(
                row,
                start_col+1,
                float(sheet.get("total") or 0.0),
                subtotal_value_fmt,
            )
            ws.set_row(row, 22)
            row += 1

            # 2) Total Quantity
            ws.write(row, start_col, _("Total Quantity"), subtotal_label_fmt)
            ws.write_number(
                row,
                start_col+1,
                float(sheet.get("qty_total") or 0.0),
                subtotal_value_fmt,
            )
            ws.set_row(row, 22)
            row += 1

            # 3) Base Unit Cost  (มาจาก stock valuation เดิม)
            ws.write(row, start_col, _("Goods Unit Cost"), subtotal_label_fmt)
            ws.write_number(
                row,
                start_col+1,
                float(sheet.get("base_unit_cost") or 0.0),
                subtotal_value_fmt,
            )
            ws.set_row(row, 22)
            row += 1

            # 4) Landed Cost / Unit  (Total Landed Cost / Qty)
            ws.write(row, start_col, _("Landed Cost / Unit"), subtotal_label_fmt)
            ws.write_number(
                row,
                start_col+1,
                float(sheet.get("landed_unit_cost") or 0.0),
                subtotal_value_fmt,
            )
            ws.set_row(row, 22)
            row += 1

            # 5) Total Unit Cost = Base + Landed
            ws.write(row, start_col, _("Total Unit Cost"), subtotal_label_fmt)
            ws.write_number(
                row,
                start_col+1,
                float(sheet.get("unit_cost") or 0.0),
                subtotal_value_fmt,
            )
            ws.set_row(row, 22)
            row += 2

            # ==== ตาราง 2: Allocation by Product (ถ้ามี) ====
            product_lines = sheet.get("product_lines") or []
            if product_lines:
                ws.merge_range(row, start_col, row, start_col+5, _("Allocation by Product"), section_header_fmt)
                ws.set_row(row, 22)
                row += 1

                headers = [
                    _("Product"),
                    _("Quantity"),
                    _("Additional Cost"),
                    _("Final Cost"),
                    _("Add. Cost / Unit"),
                    _("Final Cost / Unit"),
                ]
                
                for col, h in enumerate(headers):
                    ws.write(row, start_col+col, h, header_table_fmt)
                ws.set_row(row, 22)
                row += 1

                for pline in product_lines:
                    ws.write(row, start_col, pline.get("name") or "", normal_fmt)
                    ws.write_number(
                        row,
                        start_col+1,
                        float(pline.get("qty") or 0.0),
                        qty_fmt,
                    )
                    ws.write_number(
                        row,
                        start_col+2,
                        float(pline.get("additional") or 0.0),
                        num_fmt,
                    )
                    ws.write_number(
                        row,
                        start_col+3,
                        float(pline.get("final") or 0.0),
                        num_fmt,
                    )
                    ws.write_number(
                        row,
                        start_col+4,
                        float(pline.get("unit_cost_add") or 0.0),
                        num_fmt,
                    )
                    ws.write_number(
                        row,
                        start_col+5,
                        float(pline.get("unit_cost_final") or 0.0),
                        num_fmt,
                    )
                    ws.set_row(row, 20)
                    row += 1