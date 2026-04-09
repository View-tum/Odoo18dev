import io
from datetime import datetime

from odoo import fields
from odoo.tools.misc import xlsxwriter


class StockCountExportService:
    """Service that builds the XLSX export for the stock count report."""

    def __init__(self, env):
        self.env = env

    def export(self, wizard, lines, grouped_lines):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        worksheet = workbook.add_worksheet("Stock Count")
        formats = self._prepare_formats(workbook)

        header_row = self._write_header(worksheet, wizard, formats)
        self._set_column_widths(worksheet, wizard)
        last_row = self._write_table(worksheet, wizard, lines, grouped_lines, header_row, formats)
        self._write_signature_section(worksheet, last_row + 2, formats)

        workbook.close()
        output.seek(0)
        return output.getvalue(), self._build_filename(wizard)

    def _prepare_formats(self, workbook):
        """Prepare formats matching the PDF theme colors"""
        # Theme colors
        primary_color = '#2c3e50'      # Dark blue
        secondary_color = '#34495e'    # Medium blue
        header_bg = '#ecf0f1'          # Light gray
        text_muted = '#7f8c8d'         # Gray
        editable_bg = '#f8f9fa'        # Very light gray
        border_color = '#bdc3c7'       # Light border
        
        return {
            # Report title - centered
            "title": workbook.add_format({
                "bold": True,
                "font_size": 16,
                "font_color": primary_color,
                "font_name": "Arial",
                "align": "center",
                "valign": "vcenter",
            }),
            
            # Header divider line (using bottom border)
            "title_divider": workbook.add_format({
                "bottom": 2,
                "bottom_color": secondary_color,
            }),
            
            # Metadata section
            "meta_label": workbook.add_format({
                "bold": True,
                "font_size": 11,
                "font_color": secondary_color,
                "bg_color": header_bg,
                "border": 1,
                "border_color": border_color,
                "font_name": "Arial",
            }),
            
            "meta_value": workbook.add_format({
                "font_size": 11,
                "font_color": primary_color,
                "bg_color": header_bg,
                "border": 1,
                "border_color": border_color,
                "font_name": "Arial",
            }),
            
            # Table headers
            "table_header": workbook.add_format({
                "bold": True,
                "font_size": 10,
                "font_color": "white",
                "bg_color": primary_color,
                "border": 1,
                "border_color": "#1a252f",
                "align": "center",
                "valign": "vcenter",
                "text_wrap": True,
                "font_name": "Arial",
            }),
            
            "table_header_left": workbook.add_format({
                "bold": True,
                "font_size": 10,
                "font_color": "white",
                "bg_color": primary_color,
                "border": 1,
                "border_color": "#1a252f",
                "align": "left",
                "valign": "vcenter",
                "font_name": "Arial",
            }),
            
            "table_header_right": workbook.add_format({
                "bold": True,
                "font_size": 10,
                "font_color": "white",
                "bg_color": primary_color,
                "border": 1,
                "border_color": "#1a252f",
                "align": "right",
                "valign": "vcenter",
                "font_name": "Arial",
            }),
            
            # Data cells
            "cell": workbook.add_format({
                "border": 1,
                "border_color": border_color,
                "font_size": 10,
                "font_color": primary_color,
                "valign": "vcenter",
                "font_name": "Arial",
            }),
            
            "cell_center": workbook.add_format({
                "border": 1,
                "border_color": border_color,
                "font_size": 10,
                "font_color": primary_color,
                "align": "center",
                "valign": "vcenter",
                "font_name": "Arial",
            }),
            
            "cell_right": workbook.add_format({
                "border": 1,
                "border_color": border_color,
                "font_size": 10,
                "font_color": primary_color,
                "align": "right",
                "valign": "vcenter",
                "num_format": "0.00",
                "font_name": "Arial",
            }),
            
            # Editable cells (for manual input)
            "cell_editable": workbook.add_format({
                "border": 1,
                "border_color": border_color,
                "bg_color": editable_bg,
                "font_size": 10,
                "valign": "vcenter",
                "font_name": "Arial",
            }),
            
            # Product code (monospace style)
            "product_code": workbook.add_format({
                "border": 1,
                "border_color": border_color,
                "font_size": 9,
                "font_color": text_muted,
                "font_name": "Courier New",
                "valign": "vcenter",
            }),
            
            # Location header (for grouped view)
            "location_header": workbook.add_format({
                "bold": True,
                "font_size": 12,
                "font_color": secondary_color,
                "bg_color": header_bg,
                "left": 4,
                "left_color": secondary_color,
                "top": 1,
                "bottom": 1,
                "right": 1,
                "border_color": border_color,
                "font_name": "Arial",
            }),
            
            # Alternating row background
            "cell_alt": workbook.add_format({
                "border": 1,
                "border_color": border_color,
                "font_size": 10,
                "font_color": primary_color,
                "bg_color": "#fafafa",
                "valign": "vcenter",
                "font_name": "Arial",
            }),
            
            "cell_center_alt": workbook.add_format({
                "border": 1,
                "border_color": border_color,
                "font_size": 10,
                "font_color": primary_color,
                "bg_color": "#fafafa",
                "align": "center",
                "valign": "vcenter",
                "font_name": "Arial",
            }),
            
            "cell_right_alt": workbook.add_format({
                "border": 1,
                "border_color": border_color,
                "font_size": 10,
                "font_color": primary_color,
                "bg_color": "#fafafa",
                "align": "right",
                "valign": "vcenter",
                "num_format": "0.00",
                "font_name": "Arial",
            }),
            
            "cell_editable_alt": workbook.add_format({
                "border": 1,
                "border_color": border_color,
                "bg_color": "#f5f5f5",
                "font_size": 10,
                "valign": "vcenter",
                "font_name": "Arial",
            }),
            
            # Signature section formats (no borders)
            "signature_line_noborder": workbook.add_format({
                "align": "center",
                "valign": "bottom",
                "font_name": "Arial",
            }),
            
            "signature_brackets_noborder": workbook.add_format({
                "font_size": 10,
                "font_color": primary_color,
                "align": "center",
                "valign": "vcenter",
                "font_name": "Arial",
            }),
            
            "signature_role_noborder": workbook.add_format({
                "font_size": 10,
                "font_color": primary_color,
                "bold": True,
                "align": "center",
                "valign": "vcenter",
                "font_name": "Arial",
            }),
            
            "signature_date_noborder": workbook.add_format({
                "font_size": 9,
                "font_color": primary_color,
                "align": "center",
                "valign": "vcenter",
                "font_name": "Arial",
            }),
        }

    def _write_header(self, worksheet, wizard, formats):
        """Write professional header section"""
        company = wizard.env.company
        timestamp = fields.Datetime.context_timestamp(wizard, datetime.utcnow())
        
        row = 0
        
        # Title - merge A to G and center
        num_cols = len(self._build_headers(wizard))
        worksheet.merge_range(row, 0, row, num_cols - 1, "STOCK COUNT REPORT", formats["title"])
        row += 1
        
        # Title divider
        worksheet.merge_range(row, 0, row, num_cols - 1, "", formats["title_divider"])
        row += 2
        
        # Metadata section - larger font, no Mode
        worksheet.write(row, 0, "Company:", formats["meta_label"])
        worksheet.merge_range(row, 1, row, 2, company.display_name, formats["meta_value"])
        worksheet.write(row, 3, "Printed:", formats["meta_label"])
        worksheet.merge_range(row, 4, row, num_cols - 1, timestamp.strftime("%Y-%m-%d %H:%M:%S"), formats["meta_value"])
        row += 1
        
        worksheet.write(row, 0, "Locations:", formats["meta_label"])
        worksheet.merge_range(row, 1, row, num_cols - 1, wizard._get_selected_location_names(), formats["meta_value"])
        
        row += 3  # Space before table
        return row

    def _set_column_widths(self, worksheet, wizard):
        """Set column widths"""
        widths = [6]  # No.
        if not wizard.page_break_by_location:
            widths.append(20)  # Location
        widths += [40, 20]  # Product, Lot/Serial
        widths.append(14)  # Counted Qty
        if wizard.show_uom:
            widths.append(12)  # UoM
        widths += [12, 20]  # Price, Remark
        
        for idx, width in enumerate(widths):
            worksheet.set_column(idx, idx, width)

    def _write_table(self, worksheet, wizard, lines, grouped_lines, start_row, formats):
        """Write table data with alternating row colors"""
        headers = self._build_headers(wizard)
        row = start_row
        counter = 1
        page_break_rows = []

        if wizard.page_break_by_location:
            for group_index, group in enumerate(grouped_lines):
                if group_index:
                    page_break_rows.append(row)
                
                # Location header row - BEFORE column headers
                num_cols = len(headers)
                worksheet.merge_range(
                    row, 0, row, num_cols - 1,
                    f"Location: {group['location_name']}",
                    formats["location_header"]
                )
                row += 1
                
                # Write table headers
                col = 0
                for header in headers:
                    if header in ["No.", "Counted Qty", "Price", "Remark"]:
                        worksheet.write(row, col, header, formats["table_header"])
                    else:
                        worksheet.write(row, col, header, formats["table_header_left"])
                    col += 1
                row += 1
                
                for line in group["lines"]:
                    row = self._write_data_row(
                        worksheet, wizard, line, row, counter, formats,
                        group.get("location_name"), is_alternate=(counter % 2 == 0)
                    )
                    counter += 1
                row += 1  # Space after group
            
            if page_break_rows:
                worksheet.set_h_pagebreaks(page_break_rows)
        else:
            # Write table headers once for non-grouped view
            col = 0
            for header in headers:
                if header in ["No.", "Counted Qty", "Price", "Remark"]:
                    worksheet.write(row, col, header, formats["table_header"])
                elif header in ["System Qty"]:
                    worksheet.write(row, col, header, formats["table_header_right"])
                else:
                    worksheet.write(row, col, header, formats["table_header_left"])
                col += 1
            row += 1
            
            for line in lines:
                row = self._write_data_row(
                    worksheet, wizard, line, row, counter, formats,
                    line.get("location_name"), is_alternate=(counter % 2 == 0)
                )
                counter += 1
        
        return row

    def _build_headers(self, wizard):
        """Build table headers"""
        headers = ["No."]
        if not wizard.page_break_by_location:
            headers.append("Location")
        headers += ["Product", "Lot/Serial"]
        headers.append("Counted Qty")
        if wizard.show_uom:
            headers.append("UoM")
        headers += ["Price", "Remark"]
        return headers

    def _format_product(self, line):
        # product_name มาจาก product.display_name ซึ่งมี [default_code] อยู่แล้ว
        return line.get("product_name") or ""

    def _write_data_row(self, worksheet, wizard, line, row, counter, formats, location_name, is_alternate=False):
        """Write a single data row with alternating colors"""
        # Select format based on alternating rows
        cell_fmt = formats["cell_alt"] if is_alternate else formats["cell"]
        cell_center_fmt = formats["cell_center_alt"] if is_alternate else formats["cell_center"]
        cell_right_fmt = formats["cell_right_alt"] if is_alternate else formats["cell_right"]
        cell_editable_fmt = formats["cell_editable_alt"] if is_alternate else formats["cell_editable"]

        col = 0

        # No.
        worksheet.write_number(row, col, counter, cell_center_fmt)
        col += 1

        # Location (if not grouped)
        if not wizard.page_break_by_location:
            worksheet.write(row, col, location_name or "", cell_fmt)
            col += 1

        # Product
        worksheet.write(row, col, self._format_product(line), cell_fmt)
        col += 1

        # Lot/Serial
        worksheet.write(row, col, line.get("lot_name") or "", cell_fmt)
        col += 1

        # Counted Qty (editable) - prefill ได้
        counted = line.get("counted_qty")
        if isinstance(counted, (int, float)):
            worksheet.write_number(row, col, counted, cell_editable_fmt)
        else:
            worksheet.write(row, col, counted or "", cell_editable_fmt)
        col += 1

        # UoM
        if wizard.show_uom:
            worksheet.write(row, col, line.get("uom_name") or "", cell_fmt)
            col += 1

        # ✅ Price (editable) - ใส่เลขได้
        price = line.get("price")
        if isinstance(price, (int, float)):
            worksheet.write_number(row, col, price, cell_editable_fmt)
        else:
            worksheet.write(row, col, price or "", cell_editable_fmt)
        col += 1

        # ✅ Remark (editable)
        note = line.get("note")
        worksheet.write(row, col, note or "", cell_editable_fmt)

        return row + 1

    def _write_signature_section(self, worksheet, start_row, formats):
        """Write signature section matching PDF design - 3 columns each with 1 space between"""
        row = start_row
        
        # Set row heights for signature section
        worksheet.set_row(row, 40)      # Space for signature line
        worksheet.set_row(row + 1, 20)  # Brackets
        worksheet.set_row(row + 2, 20)  # Role
        worksheet.set_row(row + 3, 20)  # Date
        
        # Left column: ผู้ตรวจนับ (columns 0-2)
        # Signature line (empty space)
        worksheet.merge_range(row, 0, row, 2, "", formats["signature_line_noborder"])
        
        # Brackets
        worksheet.merge_range(row + 1, 0, row + 1, 2, 
                            "( ________________________________ )", 
                            formats["signature_brackets_noborder"])
        
        # Role
        worksheet.merge_range(row + 2, 0, row + 2, 2, "ผู้ตรวจนับ", formats["signature_role_noborder"])
        
        # Date
        worksheet.merge_range(row + 3, 0, row + 3, 2, 
                            "วันที่: _____ / _____ / __________", 
                            formats["signature_date_noborder"])
        
        # Empty column (column 3) - space between signatures
        # No borders needed
        
        # Right column: ผู้อนุมัติ (columns 4-6)
        # Signature line (empty space)
        worksheet.merge_range(row, 4, row, 6, "", formats["signature_line_noborder"])
        
        # Brackets
        worksheet.merge_range(row + 1, 4, row + 1, 6, 
                            "( ________________________________ )", 
                            formats["signature_brackets_noborder"])
        
        # Role
        worksheet.merge_range(row + 2, 4, row + 2, 6, "ผู้อนุมัติ", formats["signature_role_noborder"])
        
        # Date
        worksheet.merge_range(row + 3, 4, row + 3, 6, 
                            "วันที่: _____ / _____ / __________", 
                            formats["signature_date_noborder"])

    def _build_filename(self, wizard):
        """Build filename with timestamp"""
        timestamp = fields.Datetime.context_timestamp(wizard, datetime.utcnow())
        return f"stock_count_report_{timestamp.strftime('%Y%m%d_%H%M%S')}.xlsx"