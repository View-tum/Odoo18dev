# models/cost_sheet_xlsx.py
from odoo import models, fields, _


class CostSheetXlsx(models.AbstractModel):
    _name = "report.cost_sheet.report_cost_sheet_xlsx"
    _description = "Cost Sheet XLSX"
    _inherit = "report.report_xlsx.abstract"

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
        sheets  = payload.get("sheets", []) or []

        # =========================================================
        #  Color Palette — Modern Monochrome (ตรงกับ Stock Card)
        # =========================================================
        COLOR_DARK        = "#212529"   # หัวตาราง / Title bg
        COLOR_INFO_LABEL  = "#E9ECEF"   # Label bg ส่วน info
        COLOR_INFO_VALUE  = "#FFFFFF"   # Value bg ส่วน info
        COLOR_TOTAL_BG    = "#E2E3E5"   # Total row  (= opening-row ใน SC)
        COLOR_SUMMARY_BG  = "#F1F3F5"   # Summary row (= balance-cell ใน SC)
        COLOR_EVEN_BG     = "#F8F9FA"   # Alternating row
        COLOR_WHITE       = "#FFFFFF"
        COLOR_FONT_LIGHT  = "#FFFFFF"
        COLOR_FONT_DARK   = "#212529"
        COLOR_FONT_SUB    = "#383D41"
        COLOR_BORDER_HD   = "#FFFFFF"   # Border ภายในหัวตาราง
        COLOR_BORDER_INFO = "#BFBFBF"   # Border ส่วน info
        COLOR_BORDER_DATA = "#D0D0D0"   # Border ทั่วไปในตาราง

        FONT = "Tahoma"

        # =========================================================
        #  Format Definitions
        # =========================================================

        # ----- Title -----
        fmt_title = workbook.add_format({
            "bold":       True,
            "font_size":  18,
            "font_name":  FONT,
            "align":      "center",
            "valign":     "vcenter",
            "bg_color":   COLOR_DARK,
            "font_color": COLOR_FONT_LIGHT,
            "border":     0,
        })

        # ----- Info section: label -----
        fmt_info_label = workbook.add_format({
            "bold":         True,
            "font_size":    10,
            "font_name":    FONT,
            "align":        "left",
            "valign":       "vcenter",
            "bg_color":     COLOR_INFO_LABEL,
            "border":       1,
            "border_color": COLOR_BORDER_INFO,
        })

        # ----- Info section: value -----
        fmt_info_value = workbook.add_format({
            "font_size":    10,
            "font_name":    FONT,
            "align":        "left",
            "valign":       "vcenter",
            "bg_color":     COLOR_INFO_VALUE,
            "border":       1,
            "border_color": COLOR_BORDER_INFO,
            "text_wrap":    False,
        })

        # ----- Section header (e.g. "Cost Components") -----
        fmt_section_hdr = workbook.add_format({
            "bold":         True,
            "font_size":    11,
            "font_name":    FONT,
            "align":        "left",
            "valign":       "vcenter",
            "bg_color":     COLOR_DARK,
            "font_color":   COLOR_FONT_LIGHT,
            "border":       1,
            "border_color": COLOR_BORDER_HD,
        })

        # ----- Table column header -----
        fmt_col_hdr = workbook.add_format({
            "bold":         True,
            "font_size":    10,
            "font_name":    FONT,
            "align":        "center",
            "valign":       "vcenter",
            "bg_color":     COLOR_DARK,
            "font_color":   COLOR_FONT_LIGHT,
            "border":       1,
            "border_color": COLOR_BORDER_HD,
            "text_wrap":    True,
        })

        # ----- Normal cell (text) -----
        fmt_normal = workbook.add_format({
            "font_size":    10,
            "font_name":    FONT,
            "align":        "left",
            "valign":       "vcenter",
            "border":       1,
            "border_color": COLOR_BORDER_DATA,
        })

        # ----- Number cell -----
        fmt_num = workbook.add_format({
            "font_size":    10,
            "font_name":    FONT,
            "align":        "right",
            "valign":       "vcenter",
            "border":       1,
            "border_color": COLOR_BORDER_DATA,
            "num_format":   "#,##0.00",
        })

        # ----- Quantity cell (ใช้ format เดียวกับ num แต่แยกไว้เผื่อ UoM) -----
        fmt_qty = workbook.add_format({
            "font_size":    10,
            "font_name":    FONT,
            "align":        "right",
            "valign":       "vcenter",
            "border":       1,
            "border_color": COLOR_BORDER_DATA,
            "num_format":   "#,##0.00",
        })

        # ----- Total row: label (= opening-row ใน SC) -----
        fmt_total_label = workbook.add_format({
            "bold":         True,
            "font_size":    10,
            "font_name":    FONT,
            "align":        "left",
            "valign":       "vcenter",
            "bg_color":     COLOR_TOTAL_BG,
            "font_color":   COLOR_FONT_SUB,
            "border":       1,
            "border_color": COLOR_BORDER_DATA,
        })

        # ----- Total row: value -----
        fmt_total_value = workbook.add_format({
            "bold":         True,
            "font_size":    10,
            "font_name":    FONT,
            "align":        "right",
            "valign":       "vcenter",
            "bg_color":     COLOR_TOTAL_BG,
            "font_color":   COLOR_FONT_SUB,
            "border":       1,
            "border_color": COLOR_BORDER_DATA,
            "num_format":   "#,##0.00",
        })

        # ----- Summary row: label (= balance-cell ใน SC) -----
        fmt_summary_label = workbook.add_format({
            "bold":         True,
            "font_size":    10,
            "font_name":    FONT,
            "align":        "left",
            "valign":       "vcenter",
            "bg_color":     COLOR_SUMMARY_BG,
            "font_color":   COLOR_FONT_SUB,
            "border":       1,
            "border_color": COLOR_BORDER_DATA,
        })

        # ----- Total row: label right-aligned (สำหรับ merge A-F) -----
        fmt_total_label_r = workbook.add_format({
            "bold":         True,
            "font_size":    10,
            "font_name":    FONT,
            "align":        "right",
            "valign":       "vcenter",
            "bg_color":     COLOR_TOTAL_BG,
            "font_color":   COLOR_FONT_SUB,
            "border":       1,
            "border_color": COLOR_BORDER_DATA,
        })

        # ----- Summary row: label right-aligned (สำหรับ merge A-F) -----
        fmt_summary_label_r = workbook.add_format({
            "bold":         True,
            "font_size":    10,
            "font_name":    FONT,
            "align":        "right",
            "valign":       "vcenter",
            "bg_color":     COLOR_SUMMARY_BG,
            "font_color":   COLOR_FONT_SUB,
            "border":       1,
            "border_color": COLOR_BORDER_DATA,
        })

        # ----- Summary row: value -----
        fmt_summary_value = workbook.add_format({
            "bold":         True,
            "font_size":    10,
            "font_name":    FONT,
            "align":        "right",
            "valign":       "vcenter",
            "bg_color":     COLOR_SUMMARY_BG,
            "font_color":   COLOR_FONT_SUB,
            "border":       1,
            "border_color": COLOR_BORDER_DATA,
            "num_format":   "#,##0.00",
        })

        # =========================================================
        #  Build Worksheets
        # =========================================================
        for idx, sheet in enumerate(sheets, start=1):
            ws_name = (sheet.get("title") or _("Cost Sheet %s") % idx)[:31]
            ws = workbook.add_worksheet(ws_name)

            C = 0   # start column (A)

            # ----- Column widths -----
            ws.set_column(C,   C,   30)   # A  Labels / Product name
            ws.set_column(C+1, C+1, 14)   # B  Quantity
            ws.set_column(C+2, C+2, 16)   # C  Additional Cost
            ws.set_column(C+3, C+3, 16)   # D  Final Cost
            ws.set_column(C+4, C+4, 16)   # E  Unit Cost
            ws.set_column(C+5, C+5, 16)   # F  Add. Cost / Unit
            ws.set_column(C+6, C+6, 16)   # G  Final Cost / Unit

            row = 0

            # ══════════════════════════════════════════════════
            #  TITLE
            # ══════════════════════════════════════════════════
            ws.merge_range(row, C, row, C+6, "COST SHEET", fmt_title)
            ws.set_row(row, 30)
            row += 2

            # ══════════════════════════════════════════════════
            #  HEADER INFO  (4-column: label | value | label | value)
            # ══════════════════════════════════════════════════
            def _info_row(label1, val1, label2="", val2=""):
                """เขียน 1 แถว info แบบ 4 คอลัมน์
                Layout: A=label1 | B-C=val1 | D=label2 | E-G=val2
                """
                nonlocal row
                if not val1 and not val2:
                    return
                ws.write(row, C,   label1, fmt_info_label)                    # A
                ws.merge_range(row, C+1, row, C+2, val1, fmt_info_value)      # B-C
                ws.write(row, C+3, label2, fmt_info_label)                    # D
                ws.merge_range(row, C+4, row, C+6, val2, fmt_info_value)      # E-G
                ws.set_row(row, 20)
                row += 1

            def _info_full(label, val):
                """เขียน 1 แถว info แบบ label + merge ทั้งแถว"""
                nonlocal row
                if not val:
                    return
                ws.write(row, C, label, fmt_info_label)
                ws.merge_range(row, C+1, row, C+6, val, fmt_info_value)
                ws.set_row(row, 20)
                row += 1

            lc_title = sheet.get("title") or ""
            lc_date  = sheet.get("lc_date") or ""
            lc_label = ("%s  (%s)" % (lc_title, lc_date)) if lc_date else lc_title

            period = "%s  –  %s" % (sheet.get("date_from") or "", sheet.get("date_to") or "")

            _info_row("Company:",   sheet.get("company") or "", "Period:",  period)
            _info_full("Landed Cost:", lc_label)
            _info_row("Vendor:",    sheet.get("vendor") or "",  "Vendor Bill:", sheet.get("vendor_bill") or "")
            _info_row("Journal Entry:", sheet.get("journal_entry") or "", "Journal:", sheet.get("journal") or "")
            _info_full("Transfers:", sheet.get("pickings") or "")
            _info_row("Transfer JE:", sheet.get("transfer_journal_entry") or "", "Transfer Journal:", sheet.get("transfer_journal") or "")
            _info_full("Description:", sheet.get("description") or "")

            row += 1  # เว้นบรรทัดก่อนตาราง

            # ══════════════════════════════════════════════════
            #  TABLE 1: Cost Components
            # ══════════════════════════════════════════════════
            ws.merge_range(row, C, row, C+6, _("Cost Components"), fmt_section_hdr)
            ws.set_row(row, 22)
            row += 1

            ws.merge_range(row, C, row, C+5, _("Item"),   fmt_col_hdr)   # A-F
            ws.write(row, C+6, _("Amount"), fmt_col_hdr)                  # G
            ws.set_row(row, 22)
            row += 1

            for line in sheet.get("lines", []) or []:
                ws.merge_range(row, C, row, C+5, line.get("name") or "", fmt_normal)   # A-F
                ws.write_number(row, C+6, float(line.get("amount") or 0.0), fmt_num)   # G
                ws.set_row(row, 20)
                row += 1

            # Total Landed Cost  → total row, label A-F (right), value G
            ws.merge_range(row, C, row, C+5, _("Total Landed Cost"), fmt_total_label_r)
            ws.write_number(row, C+6, float(sheet.get("total") or 0.0), fmt_total_value)
            ws.set_row(row, 22)
            row += 1

            # Summary rows → label A-F (right), value G
            for label, key in [
                (_("Total Quantity"),      "qty_total"),
                (_("Total Goods"),         "total_goods"),
                (_("Total Shipment Cost"), "total_shipment_cost"),
            ]:
                ws.merge_range(row, C, row, C+5, label, fmt_summary_label_r)
                ws.write_number(row, C+6, float(sheet.get(key) or 0.0), fmt_summary_value)
                ws.set_row(row, 22)
                row += 1

            row += 1  # เว้นก่อนตารางถัดไป

            # ══════════════════════════════════════════════════
            #  TABLE 2: Allocation by Product
            # ══════════════════════════════════════════════════
            product_lines = sheet.get("product_lines") or []
            if product_lines:
                ws.merge_range(row, C, row, C+6, _("Allocation by Product"), fmt_section_hdr)
                ws.set_row(row, 22)
                row += 1

                col_headers = [
                    _("Product"),
                    _("Quantity"),
                    _("Additional Cost"),
                    _("Final Cost"),
                    _("Unit Cost"),
                    _("Add. Cost / Unit"),
                    _("Final Cost / Unit"),
                ]
                for col_offset, h in enumerate(col_headers):
                    ws.write(row, C + col_offset, h, fmt_col_hdr)
                ws.set_row(row, 22)
                row += 1

                for pline in product_lines:
                    ws.write(row, C,   pline.get("name") or "", fmt_normal)
                    ws.write_number(row, C+1, float(pline.get("qty")            or 0.0), fmt_qty)
                    ws.write_number(row, C+2, float(pline.get("additional")     or 0.0), fmt_num)
                    ws.write_number(row, C+3, float(pline.get("final")          or 0.0), fmt_num)
                    ws.write_number(row, C+4, float(pline.get("unit_cost")      or 0.0), fmt_num)
                    ws.write_number(row, C+5, float(pline.get("unit_cost_add")  or 0.0), fmt_num)
                    ws.write_number(row, C+6, float(pline.get("unit_cost_final") or 0.0), fmt_num)
                    ws.set_row(row, 20)
                    row += 1