import base64
from odoo import models, fields, api
from ..report.expense_report_xlsx import AccountExpenseTransactionXlsx


class AccountExpenseReportWizard(models.TransientModel):
    _name = "account.expense.report.wizard"
    _description = "Account Expense Report"

    product_ids = fields.Many2many(
        comodel_name="product.product",
        string="สินค้า/บริการ",
        required=True,
        domain="[('type', '=', 'service'), ('old_default_code', 'ilike', '9')]",
        help="(365 custom) เลือกเฉพาะสินค้าประเภทบริการที่มีรหัสเก่าเริ่มต้นด้วย '9'",
    )
    vendor_id = fields.Many2one(
        comodel_name="res.partner",
        string="ผู้จำหน่าย",
        domain="[('supplier_rank', '>', 0)]",
        help="(365 custom) เลือกเฉพาะคู่ค้าที่ยังมีสถานะเป็นผู้จำหน่าย",
    )
    start_date = fields.Date(
        string="วันที่เริ่มต้น",
        required=True,
        default=fields.Date.context_today,
        help="(365 custom) วันที่เริ่มต้นสำหรับการกรองข้อมูลรายงาน",
    )
    end_date = fields.Date(
        string="วันที่สิ้นสุด",
        required=True,
        default=fields.Date.context_today,
        help="(365 custom) วันที่สิ้นสุดสำหรับการกรองข้อมูลรายงาน",
    )
    report_id = fields.Many2one(
        comodel_name="jasper.report",
        string="รายงาน",
        domain=[("model_id.model", "=", _name)],
        help="(365 custom) เลือกระบุรายงานที่ต้องการ",
    )

    @api.model
    def default_get(self, fields_list):
        """Initialize default values for dates and report template."""
        res = super(AccountExpenseReportWizard, self).default_get(fields_list)
        if "report_id" in fields_list and not res.get("report_id"):
            found_report = self.env["jasper.report"].search(
                [("model_id", "=", self._name)], order="id", limit=1
            )
            if found_report:
                res["report_id"] = found_report.id
        return res

    def _print_debug_log(self, expense_data):
        """ฟังก์ชันภายใน (Helper/Private) สำหรับ Print Log แยกส่วนโครงสร้างข้อมูลออกมาแสดงผล"""
        print("\n" + "=" * 80)
        print(" [DEBUG] STARTING EXPENSE REPORT DATA EXPORT ".center(80, "="))
        print("=" * 80)

        for product_group in expense_data:
            print(
                f"\n📦 PRODUCT CODE: {product_group.get('product_code')} | PRODUCT NAME: {product_group.get('product_name')}"
            )
            print("-" * 80)

            expenses = product_group.get("expense_data", [])
            if not expenses:
                print("   🚫 No Expense Data Found for this product.")
                continue

            for idx, exp in enumerate(expenses, 1):
                print(f"\n   📌 [Expense Entry #{idx}]")
                print("   " + "~" * 40)
                # --- ส่วนที่ 1: Print Header ---
                print("   📑 [HEADER DATA]")
                print(f"      • Vendor Bill : {exp.get('vendor_bill')}")
                print(f"      • Vendor Name : {exp.get('vendor_name')}")
                print(f"      • Label/Desc  : {exp.get('label')}")
                print(
                    f"      • Period      : {exp.get('start_date')} ถึง {exp.get('end_date')}"
                )
                print(f"      • Acquisition : {exp.get('acquisition'):,.2f}")
                print(f"      • Status      : {exp.get('status')}")

                # --- ส่วนที่ 2: Print Transactions ---
                txs = exp.get("transactions", [])
                print(f"\n   🔄 [TRANSACTIONS DATA] (Total: {len(txs)} items)")
                if not txs:
                    print("      • No deferred transactions available.")
                else:
                    for t_idx, tx in enumerate(txs, 1):
                        print(
                            f"      👉 ({t_idx}) Date: {tx.get('date')} | Voucher: {tx.get('voucher')} | Type: {tx.get('type')} | Amount: {tx.get('amount'):,.2f} {tx.get('currency')}"
                        )
                        print(f"          Description: {tx.get('description') or '-'}")

                print("   " + "~" * 40)
            print("-" * 80)

        print("\n" + "=" * 80)
        print(" [DEBUG] END OF EXPENSE REPORT DATA ".center(80, "="))
        print("=" * 80 + "\n")

    def get_report_data(self):
        """ฟังก์ชันสำหรับดึงข้อมูลและจัดโครงสร้างส่งให้ Excel"""
        self.ensure_one()
        if self.start_date and self.end_date and self.start_date > self.end_date:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "วันที่ไม่ถูกต้อง",
                    "message": "  • วันที่เริ่มต้น ต้องมาก่อน หรือวันเดียวกับ วันที่สิ้นสุด",
                    "type": "warning",
                    "sticky": False,
                },
            }

        report_data_by_product = []
        for product in self.product_ids:
            domain = [
                ("product_id", "=", product.id),
                ("move_id.date", ">=", self.start_date),
                ("move_id.date", "<=", self.end_date),
                ("move_id.state", "=", "posted"),
                ("move_id.move_type", "=", "in_invoice"),
                ("deferred_start_date", "!=", False),
                ("deferred_end_date", "!=", False),
            ]
            if self.vendor_id:
                domain.append(("move_id.partner_id", "=", self.vendor_id.id))

            invoice_lines = self.env["account.move.line"].search(domain)
            expense_data = []

            for line in invoice_lines:
                bill = line.move_id

                full_name = line.name or ""
                product_prefix = (
                    f"[{line.product_id.default_code}] {line.product_id.name}"
                )

                product_label = full_name.replace(product_prefix, "").strip()

                if not product_label and line.product_id.name:
                    product_label = product_prefix

                if product_label.startswith("\n"):
                    product_label = product_label.lstrip("\n").strip()

                deferred_bills = bill.deferred_move_ids.filtered(
                    lambda am: am.state == "posted"
                )

                raw_transactions = []
                for am in deferred_bills:
                    if not any(full_name in (l.name or "") for l in am.line_ids):
                        continue

                    is_acquisition = am.amount_total == line.price_subtotal
                    raw_transactions.append(
                        {
                            "date": am.date,
                            "voucher": am.name,
                            "description": am.ref or "",
                            "type": "Acquisition" if is_acquisition else "Prepaid",
                            "amount": (
                                am.amount_total
                                if is_acquisition
                                else -(am.amount_total)
                            ),
                            "currency": am.currency_id.name or "",
                        }
                    )

                acquisition_txs = [
                    t for t in raw_transactions if t["type"] == "Acquisition"
                ]
                prepaid_txs = [t for t in raw_transactions if t["type"] == "Prepaid"]
                prepaid_txs.sort(
                    key=lambda x: (fields.Date.from_string(x["date"]), x["voucher"])
                )
                sorted_transactions = acquisition_txs + prepaid_txs

                sum_transaction = sum(
                    tx.get("amount", 0.0) for tx in sorted_transactions
                )

                if round(sum_transaction, 2) != 0.0:
                    expense_status = "Opening"
                else:
                    expense_status = "Closed"

                expense_data.append(
                    {
                        "product": f"[{product.default_code}] {product.name}",
                        "vendor_bill": bill.name,
                        "vendor_name": bill.partner_id.name,
                        "label": product_label,
                        "start_date": line.deferred_start_date,
                        "end_date": line.deferred_end_date,
                        "status": expense_status,
                        "acquisition": line.price_subtotal,
                        "balance": bill.amount_total,
                        "transactions": sorted_transactions,
                    }
                )

            report_data_by_product.append(
                {
                    "product_code": product.default_code or "",
                    "product_name": product.name or "",
                    "expense_data": expense_data,
                }
            )

        return report_data_by_product

    def export_to_excel(self):
        """ฟังก์ชันสำหรับส่งออกข้อมูลเป็น Excel"""
        self.ensure_one()

        expense_data = self.get_report_data()

        # ======================================================================
        # เรียกใช้งานฟังก์ชันสำหรับ Print Log แยก (Clean Code)
        # ======================================================================
        # self._print_debug_log(expense_data)
        # ======================================================================

        excel_reporter = AccountExpenseTransactionXlsx()
        excel_binary = excel_reporter.generate_excel(expense_data)

        attachment_values = {
            "name": f"Expense_Report_{fields.Date.to_string(fields.Date.today())}.xlsx",
            "datas": base64.b64encode(excel_binary),
            "res_model": "account.expense.report.wizard",
            "res_id": self.id,
            "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }
        attachment = self.env["ir.attachment"].create(attachment_values)

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "self",
        }

    def print_report(self):
        """ฟังก์ชันสำหรับดึงข้อมูลและส่งต่อไปยัง Jasper Report"""
        self.ensure_one()
        if self.start_date and self.end_date and self.start_date > self.end_date:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "วันที่ไม่ถูกต้อง",
                    "message": "  • วันที่เริ่มต้น ต้องมาก่อน หรือวันเดียวกับ วันที่สิ้นสุด",
                    "type": "warning",
                    "sticky": False,
                },
            }

        if not self.report_id:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "การตั้งค่าไม่ถูกต้อง",
                    "message": "  • ไม่พบรายงาน Jasper Report กรุณาตรวจสอบการตั้งค่า",
                    "type": "warning",
                    "sticky": False,
                },
            }

        product_ids = (
            ",".join(map(str, self.product_ids.ids)) if self.product_ids else None
        )
        vendor_id = str(self.vendor_id.id) if self.vendor_id else None
        start_date = self.start_date.strftime("%Y-%m-%d") if self.start_date else None
        end_date = self.end_date.strftime("%Y-%m-%d") if self.end_date else None
        data = {
            "product_ids": product_ids,
            "vendor_id": vendor_id,
            "date_from": start_date,
            "date_to": end_date,
        }
        return self.report_id.run_report(docids=[self.ids[0]], data=data)
