import math
from datetime import date

from odoo import models, fields, api


class ChequeReport(models.TransientModel):
    _name = "cheque.report"
    _description = "Cheque Report"

    cheque_ids = fields.Many2many(
        comodel_name="cheque.inbound.outbound",
        string="Cheque",
        default=lambda self: self.env.context.get("active_ids"),
    )
    cheque_date = fields.Date(string="Cheque Date", help="(365 custom) วันที่ของเช็ค.")
    report_id = fields.Many2one(
        comodel_name="jasper.report",
        domain=[("model_id", "=", _name)],
        string="Report",
        help="(365 custom) เทมเพลตรายงานที่จะใช้ในการสร้างเอกสาร (เลือกโดยระบบตามการตั้งค่า).",
    )

    @api.model
    def default_get(self, fields_list):
        """Initialize default values for cheque_date and report template."""
        res = super(ChequeReport, self).default_get(fields_list)

        if "cheque_date" in fields_list and not res.get("cheque_date"):
            res["cheque_date"] = fields.Date.context_today(self)

        if "report_id" in fields_list and not res.get("report_id"):
            found_report = self.env["jasper.report"].search(
                [("model_id", "=", self._name)], order="id", limit=1
            )
            if found_report:
                res["report_id"] = found_report.id

        return res

    @api.model
    def datetime_bahttext(self, amount):
        """ฟังก์ชันแปลงจำนวนเงินเป็นตัวอักษรภาษาไทยแบบ Native (บาทถ้วน)"""
        if amount is None or amount == 0:
            return "ศูนย์บาทถ้วน"

        digits = [
            "ศูนย์",
            "หนึ่ง",
            "สอง",
            "สาม",
            "สี่",
            "ห้า",
            "หก",
            "เจ็ด",
            "แปด",
            "เก้า",
        ]
        positions = ["", "สิบ", "ร้อย", "พัน", "หมื่น", "แสน", "ล้าน"]

        # แยกส่วนบาทและสตางค์
        amount_str = f"{amount:.2f}"
        baht_part, satang_part = amount_str.split(".")

        def convert_chunk(number_str):
            output = ""
            length = len(number_str)
            for index, digit in enumerate(number_str):
                pos = length - index - 1
                val = int(digit)
                if val == 0:
                    continue
                if pos == 1 and val == 1:
                    output += "สิบ"
                elif pos == 1 and val == 2:
                    output += "ยี่สิบ"
                elif pos == 0 and val == 1 and length > 1:
                    output += "เอ็ด"
                else:
                    output += digits[val] + positions[pos]
            return output

        # คำนวณส่วนล้าน (ถ้ามีเงินเกินล้าน)
        baht_text = ""
        baht_len = len(baht_part)
        if baht_len > 6:
            million_part = baht_part[:-6]
            baht_part = baht_part[-6:]
            baht_text += convert_chunk(million_part) + "ล้าน"

        baht_text += convert_chunk(baht_part)
        if baht_text:
            baht_text += "บาท"
        else:
            baht_text = "ศูนย์บาท"

        if int(satang_part) == 0:
            baht_text += "ถ้วน"
        else:
            baht_text += convert_chunk(satang_part) + "สตางค์"

        return baht_text

    def get_report_data(self):
        """Prepare data for the report grouped by page (5 items per page)"""
        cheque_ids = self.cheque_ids.ids if self.cheque_ids else []
        cheques = self.env["cheque.inbound.outbound"].search(
            [("id", "in", cheque_ids), ("state", "=", "waiting_confirm")],
            order="id asc",
        )

        all_lines = []
        # today = date.today()
        # date_full = f"{today.day}      {today.month}       {today.year + 543}"
        date_now = self.cheque_date
        date_full = f"{date_now.day}      {date_now.month}       {date_now.year + 543}"
        # 1. ดึงข้อมูลดิบของทุกเช็คออกมาก่อน
        for index, cio in enumerate(cheques):
            invoice_names = []
            if hasattr(cio, "payment_ids"):
                for payment in cio.payment_ids:
                    invoices = payment.reconciled_invoice_ids.sorted(
                        key=lambda r: r.name
                    )
                    invoice_names.extend(invoices.mapped("name"))

            invoice_name_str = ", ".join(filter(None, invoice_names))

            journal = cio.bank_account_journal_id
            partner_bank = journal.bank_account_id if journal else False
            sanitized_acc_number = partner_bank.sanitized_acc_number or ""

            journal_name_en = journal.with_context(lang="en_US").name if journal else ""
            bank_number = (
                journal_name_en.split("#")[1].strip() if "#" in journal_name_en else ""
            )

            partner = cio.pay_partner_id
            salesperson = partner.user_id.partner_id if partner.user_id else False

            # คำนวณ bank_number_full แบบตัวแปรชั่วคราวตามฟอร์แมตเดิม
            bank_number_full = "                "
            for i in range(1, 11):
                current_digit = (
                    sanitized_acc_number[i - 1]
                    if len(sanitized_acc_number) >= i
                    else ""
                )
                if i in [6, 7]:
                    bank_number_space = "    "
                elif i in [1, 2, 8]:
                    bank_number_space = "     "
                elif i in [3, 4, 5, 9]:
                    bank_number_space = "      "
                bank_number_full += current_digit + bank_number_space

            # เก็บเฉพาะข้อมูลระดับ Line รายการเช็ค
            line_row = {
                "cheque_number": cio.name,
                "bank_name": cio.cheque_bank_id.name if cio.cheque_bank_id else "",
                "branch_name": cio.cheque_bank_branch,
                "cheque_date": (
                    cio.cheque_date.strftime("%d/%m/%Y") if cio.cheque_date else ""
                ),
                "cheque_amount": cio.amount,
                "partner_name": partner.name or "",
                "partner_code": partner.ref or "",
                "invoice_name": invoice_name_str,
                "sale_region": (
                    partner.salesregion_id.name if partner.salesregion_id else ""
                ),
                "saleperson_name": salesperson.name if salesperson else "",
                # ข้อมูลเหล่านี้ดึงไปใช้สร้าง Header ประจำหน้า
                "_meta_header": {
                    "date": date_full,
                    "cheque_bank_branch": "สามแยก",
                    "company_bank_name": (
                        "                                                  "
                        + partner_bank.acc_holder_name
                        if partner_bank
                        else ""
                    ),
                    "bank_number_full": bank_number_full,
                },
            }
            all_lines.append(line_row)

        # 2. แบ่งกลุ่มข้อมูลหน้าละ 5 รายการ (Chunking 5 items per page)
        pages_result = []
        items_per_page = 5
        total_items = len(all_lines)
        total_pages = math.ceil(total_items / items_per_page)

        for p in range(total_pages):
            start_idx = p * items_per_page
            end_idx = start_idx + items_per_page
            page_lines = all_lines[start_idx:end_idx]

            # คำนวณผลรวมต่างๆ เฉพาะภายในหน้านี้ (Page Logic)
            page_cheque_amount_total = sum(line["cheque_amount"] for line in page_lines)
            page_cheque_count = len(page_lines)
            page_bahttext_total = self.datetime_bahttext(page_cheque_amount_total)

            # ดึงข้อมูล Header จากรายการแรกของหน้านั้นๆ (ถ้าไม่มีให้ใช้ค่าเริ่มต้น)
            header_data = (
                page_lines[0]["_meta_header"]
                if page_lines
                else {
                    "date": date_full,
                    "cheque_bank_branch": "สามแยก",
                    "company_bank_name": "",
                    "bank_number_full": "",
                }
            )

            # ลบฟิลด์ชั่วคราวออกเพื่อความสะอาดของข้อมูล
            for line in page_lines:
                if "_meta_header" in line:
                    del line["_meta_header"]

            # ประกอบข้อมูลโครงสร้าง Excel เป็นหน้าๆ
            page_structure = {
                "page_no": p + 1,
                "header": {
                    "date": header_data["date"],
                    "cheque_bank_branch": header_data["cheque_bank_branch"],
                    "company_bank_name": header_data["company_bank_name"],
                    "bank_number_full": header_data["bank_number_full"],
                },
                "lines": page_lines,
                "footer": {
                    "page_total_amount": page_cheque_amount_total,  # 1. ผลรวม cheque_amount ใน 1 sheet
                    "page_total_bahttext": page_bahttext_total,  # 2. ผลรวมภาษาไทยประจำ sheet
                    "page_items_count": page_cheque_count,  # 3. จำนวน id ในแต่ละ sheet
                },
            }
            pages_result.append(page_structure)

        # 3. สั่งพิมพ์โครงสร้างข้อมูลออกทางคอนโซลเพื่อตรวจสอบ (Debug Print)
        print("=" * 60)
        print(f"PREPARED EXCEL DATA: TOTAL PAGES = {len(pages_result)}")
        print("=" * 60)
        for page in pages_result:
            print(f"\n--- [ SHEET / PAGE NO. {page['page_no']} ] ---")
            print("  [HEADER]")
            for k, v in page["header"].items():
                print(f"    {k}: {v!r}")
            print(f"  [LINES] (Count: {len(page['lines'])})")
            for idx, line in enumerate(page["lines"], start=1):
                print(
                    f"    Line {idx}: {line['cheque_number']} | Amount: {line['cheque_amount']} | {line['partner_name']}"
                )
            print("  [FOOTER]")
            for k, v in page["footer"].items():
                print(f"    {k}: {v!r}")
        print("=" * 60)

        return pages_result

    def action_excel_export(self):
        """ปุ่มสำหรับส่ง Action URL เพื่อกระตุ้นให้เบราว์เซอร์ดาวน์โหลดไฟล์ Excel"""
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/cheque_report/export_excel?wizard_id={self.id}",
            "target": "new",
        }

    def action_print(self):
        """Logic สำหรับการสั่งพิมพ์ Report"""
        self.ensure_one()

        if not self.report_id:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "การตั้งค่าไม่ถูกต้อง",
                    "message": "  • ไม่พบรายงาน กรุณาเลือกรายงาน",
                    "type": "warning",
                    "sticky": False,
                },
            }

        cheque_ids = (
            ",".join(map(str, self.cheque_ids.ids)) if self.cheque_ids else None
        )
        cheque_date = (
            self.cheque_date.strftime("%Y-%m-%d") if self.cheque_date else None
        )

        data = {
            "cheque_ids": cheque_ids,
            "cheque_date": cheque_date,
        }

        return self.report_id.run_report(docids=[self.ids[0]], data=data)
