# inventory_stock_card/report/inventory_stock_card_mixin_xlsx.py
from odoo import models, _
from odoo.exceptions import UserError
import io, base64, xlsxwriter
from datetime import datetime

from ..utils.inventory_stock_card_utils import utc_naive_to_local_naive

class InventoryStockCardXlsxMixin(models.AbstractModel):
    _name = "inventory.stock.card.xlsx.mixin"
    _description = "Stock Card XLSX Generation Logic"

    def action_export_xlsx(self):
        self.ensure_one()
        if not self.product_ids:
            raise UserError(_("Please select at least one product."))

        payload = self._build_report_payload()
        sheets_data = payload.get('sheets', [])

        bio = io.BytesIO()
        wb = xlsxwriter.Workbook(bio, {"in_memory": True})
        
        # Font Config
        font_config = {
            'font_name': 'Angsana New',
            'font_size': 16
        }
        
        # Formats
        date_fmt = wb.add_format({
            'num_format': 'dd/mm/yyyy hh:mm:ss',
            'border': 1, 'align': 'center', 'valign': 'vcenter',
            **font_config
        })

        # [แก้ไข] ตัดหน่วยออกจาก format เพื่อให้แสดงแค่ตัวเลข
        fmt_curr = wb.add_format({'border': 1, 'align': 'right', 'valign': 'vcenter', 'num_format': '#,##0.00', **font_config})
        fmt_qty = wb.add_format({'border': 1, 'align': 'right', 'valign': 'vcenter', 'num_format': '#,##0.00', **font_config})
        fmt_bal = wb.add_format({'border': 1, 'align': 'right', 'valign': 'vcenter', 'num_format': '#,##0.00', **font_config})
        
        fmt_title_big = wb.add_format({
            'bold': True, 'font_size': 18, 'font_name': 'Angsana New',
            'align': 'center', 'valign': 'vcenter', 'border': 1
        })
        
        fmt_kv_label = wb.add_format({
            'bold': True, 'border': 1, 'align': 'left', 'valign': 'vcenter',
            **font_config
        })
        
        fmt_value_fit = wb.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter', **font_config})
        fmt_value_fit.set_shrink()
        
        fmt_hdr = wb.add_format({
            'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter',
            **font_config
        })
        
        fmt_txt = wb.add_format({
            'border': 1, 'align': 'left', 'valign': 'vcenter',
            'text_wrap': True,
            **font_config
        })
        
        fmt_txt_center = wb.add_format({
            'border': 1, 'align': 'center', 'valign': 'vcenter',
            'text_wrap': True,
            **font_config
        })

        for sheet in sheets_data:
            sheet_name = (sheet.get('product') or "StockCard")[:31]
            invalid_chars = [':', '*', '?', '/', '\\', '[', ']']
            for char in invalid_chars:
                sheet_name = sheet_name.replace(char, '')
            
            ws = wb.add_worksheet(sheet_name)
            
            # [แก้ไข] ดึงค่า Unit เพื่อเอาไปใส่ใน Header แทน
            uom_label = sheet.get('uom') or ""
            curr_symbol = sheet.get('currency_symbol') or ""
            is_at_date_only = sheet.get('at_date_only', False)

            # คำนวณความกว้างคอลัมน์ (Dynamic Column Width)
            min_width = 18.13
            max_origin_len = 20 
            max_partner_len = 20
            
            lines = sheet.get('lines', [])
            
            for line in lines:
                origin_text = str(line.get("origin") or "")
                partner_text = str(line.get("partner") or "")
                
                if '\n' in origin_text:
                    current_max = max([len(s) for s in origin_text.split('\n')]) if origin_text else 0
                    max_origin_len = max(max_origin_len, current_max)
                else:
                    max_origin_len = max(max_origin_len, len(origin_text))

                max_partner_len = max(max_partner_len, len(partner_text))
            
            # Set Column Widths
            origin_width = max(min_width, min(max_origin_len * 1.1, 50))
            partner_width = max(min_width, min(max_partner_len * 1.1, 50))
            
            ws.set_column(0, 0, 22)              # Date
            ws.set_column(1, 1, 18)              # Reference
            ws.set_column(2, 2, origin_width)    # Origin
            ws.set_column(3, 3, partner_width)   # Partner
            ws.set_column(4, 4, 18)              # Lot
            ws.set_column(5, 6, 16)              # Opening
            ws.set_column(7, 8, 16)              # In
            ws.set_column(9, 10, 16)             # Out
            ws.set_column(11, 12, 16)            # Balance
            
            # Default Height
            ws.set_default_row(24)

            # --- Header Writing ---
            ws.merge_range(0, 0, 0, 12, "รายงานสินค้าคงคลัง (Stock Card Report)", fmt_title_big)
            ws.set_row(0, 30)
            
            row_label, row_value = 2, 3
            ws.write(row_label, 0, "บริษัท (Company)", fmt_kv_label)
            ws.write(row_value, 0, sheet.get('company'), fmt_value_fit)
            ws.merge_range(row_label, 1, row_label, 2, "สินค้า (Product)", fmt_kv_label)
            ws.merge_range(row_value, 1, row_value, 2, sheet.get('product'), fmt_value_fit)
            ws.merge_range(row_label, 3, row_label, 4, "คลังสินค้า (Location)", fmt_kv_label)
            ws.merge_range(row_value, 3, row_value, 4, sheet.get('location'), fmt_value_fit)
            ws.write(row_label, 5, "วันที่เริ่มต้น (Date From)", fmt_kv_label)
            ws.write_datetime(row_value, 5, utc_naive_to_local_naive(self.env, sheet.get('date_from')), date_fmt)
            ws.write(row_label, 6, "วันที่สิ้นสุด (Date To)", fmt_kv_label)
            ws.write_datetime(row_value, 6, utc_naive_to_local_naive(self.env, sheet.get('date_to')), date_fmt)

            header_row = 5
            ws.set_row(header_row, 24)
            ws.set_row(header_row + 1, 24)
            
            ws.merge_range(header_row, 0, header_row + 1, 0, "วันที่\n(Date)", fmt_hdr)
            ws.merge_range(header_row, 1, header_row + 1, 1, "เลขที่เอกสาร\n(Reference)", fmt_hdr)
            ws.merge_range(header_row, 2, header_row + 1, 2, "เอกสารอ้างอิง\n(Origin)", fmt_hdr)
            ws.merge_range(header_row, 3, header_row + 1, 3, "คู่ค้า\n(Partner)", fmt_hdr)
            ws.merge_range(header_row, 4, header_row + 1, 4, "Lot Number", fmt_hdr)
            
            ws.merge_range(header_row, 5, header_row, 6, "ยอดยกมา (Opening)", fmt_hdr)
            ws.merge_range(header_row, 7, header_row, 8, "รับเข้า (Incoming)", fmt_hdr)
            ws.merge_range(header_row, 9, header_row, 10, "จ่ายออก (Outgoing)", fmt_hdr)
            ws.merge_range(header_row, 11, header_row, 12, "คงเหลือ (Balance)", fmt_hdr)

            # [แก้ไข] สร้าง Header ย่อยโดยใส่หน่วยเข้าไปด้วย
            qty_title = f"จำนวน\n(Qty {uom_label})" if uom_label else "จำนวน\n(Qty)"
            val_title = f"มูลค่า\n(Value {curr_symbol})" if curr_symbol else "มูลค่า\n(Value)"

            sub_headers = [
                qty_title, val_title,
                qty_title, val_title,
                qty_title, val_title,
                qty_title, val_title
            ]
            ws.write_row(header_row + 1, 5, sub_headers, fmt_hdr)
            
            ws.freeze_panes(header_row + 2, 0)

            current_row = header_row + 2

            for line in lines:
                origin_val = str(line.get("origin") or "")
                partner_val = str(line.get("partner") or "")
                
                lines_origin = origin_val.count('\n') + 1
                lines_partner = partner_val.count('\n') + 1
                
                max_lines = max(lines_origin, lines_partner)
                
                if max_lines > 1:
                    row_height = max(24, max_lines * 22)
                    ws.set_row(current_row, row_height)
                
                line_date = utc_naive_to_local_naive(self.env, line.get('date'))
                if line_date:
                    ws.write_datetime(current_row, 0, line_date, date_fmt)
                else:
                    ws.write(current_row, 0, "", fmt_txt_center)
                
                ws.write(current_row, 1, line.get("picking") or "", fmt_txt_center)
                ws.write(current_row, 2, line.get("origin") or "", fmt_txt)
                ws.write(current_row, 3, line.get("partner") or "", fmt_txt)
                ws.write(current_row, 4, line.get("lot_name") or "", fmt_txt_center)

                # [แก้ไข] ถ้าเป็น At Date Only ให้ใส่ค่าว่างแทน 0
                if not is_at_date_only:
                    ws.write(current_row, 5, line.get("line_open_qty") or 0.0, fmt_qty)
                    ws.write(current_row, 6, line.get("line_open_val") or 0.0, fmt_curr)

                    qty_in = line.get("qty_in") or 0.0
                    val_amt = line.get("valuation_amount") or 0.0
                    
                    if qty_in > 0:
                        ws.write(current_row, 7, qty_in, fmt_qty)
                        ws.write(current_row, 8, val_amt, fmt_curr)
                    else:
                        ws.write(current_row, 7, 0, fmt_qty)
                        ws.write(current_row, 8, 0, fmt_curr)

                    qty_out = line.get("qty_out") or 0.0
                    if qty_out > 0:
                        ws.write(current_row, 9, qty_out, fmt_qty)
                        ws.write(current_row, 10, val_amt, fmt_curr)
                    else:
                        ws.write(current_row, 9, 0, fmt_qty)
                        ws.write(current_row, 10, 0, fmt_curr)
                else:
                    # Write empty string with format to preserve borders
                    ws.write(current_row, 5, "", fmt_qty)
                    ws.write(current_row, 6, "", fmt_curr)
                    ws.write(current_row, 7, "", fmt_qty)
                    ws.write(current_row, 8, "", fmt_curr)
                    ws.write(current_row, 9, "", fmt_qty)
                    ws.write(current_row, 10, "", fmt_curr)

                ws.write(current_row, 11, line.get("balance_qty") or 0.0, fmt_bal)
                ws.write(current_row, 12, line.get("balance_val") or 0.0, fmt_curr)

                current_row += 1

        wb.close()
        data = base64.b64encode(bio.getvalue())
        bio.close()
        
        filename = "stock_card_%s.xlsx" % datetime.now().strftime("%Y%m%d_%H%M%S")
        att = self.env["ir.attachment"].create({
            "name": filename,
            "type": "binary",
            "datas": data,
            "res_model": self._name,
            "public": False,
        })
        
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=true" % att.id,
            "target": "self",
            "close_on_report_download": True,
        }