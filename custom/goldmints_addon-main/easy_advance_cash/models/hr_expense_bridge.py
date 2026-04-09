from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    def action_sheet_move_post(self):
        """Override: Sync to Advance Cash Log when updated"""
        res = super(HrExpenseSheet, self).action_sheet_move_post()

        for sheet in self:
            # 1. กรณีเป็น Advance Request (checkbox 'advance' = True) ---> (Payout)
            # เราต้องเช็ค field 'advance' ของ module hr_expense_advance_clearing
            if getattr(sheet, "advance", False) and sheet.account_move_ids:
                self._sync_advance_payout_log(sheet)

            # 2. กรณีเป็น Clearing (มี field 'advance_sheet_id') ---> (Expense)
            if getattr(sheet, "advance_sheet_id", False) and sheet.account_move_ids:
                self._sync_advance_clearing_log(sheet)

        return res

    def _sync_advance_payout_log(self, sheet):
        """สร้าง Logbook (Payout) จาก Expense Advance Sheet"""
        Log = self.env["advance.cash.log"]
        # เช็คก่อนว่าเคยสร้างยัง (กันซ้ำ)
        existing = Log.search([("move_id", "in", sheet.account_move_ids.ids)], limit=1)
        if existing:
            return

        move = sheet.account_move_ids[0]
        Log.create(
            {
                "date": sheet.accounting_date or fields.Date.today(),
                "transaction_type": "payout",
                "employee_id": sheet.employee_id.id,
                "description": f"Advance (Exp): {sheet.name}",
                "amount": sheet.total_amount,
                # จำลอง Journal (หา Journal ที่ใช้)
                "journal_id": sheet.journal_id.id,
                # Link Move เลย (Logbook จะไม่สร้าง Move ใหม่ แต่จะโชว์ Move นี้)
                "move_id": move.id,
                "state": "posted",
                "expense_sheet_id": sheet.id,  # Link กลับ
            }
        )

    def _sync_advance_clearing_log(self, sheet):
        """สร้าง Logbook (Expense) จาก การเคลียร์บิล"""
        Log = self.env["advance.cash.log"]
        existing = Log.search([("move_id", "in", sheet.account_move_ids.ids)], limit=1)
        if existing:
            return

        move = sheet.account_move_ids[0]

        # ค้นหา Advance Log จาก Expense Sheet ID (เผื่อเคยสร้างแล้วแต่ยังไม่ผูก Move)
        existing_log_no_move = Log.search(
            [("expense_sheet_id", "=", sheet.id)], limit=1
        )

        # Prepare Values
        line = sheet.expense_line_ids[0] if sheet.expense_line_ids else False
        vals = {
            "state": "posted",
            "move_id": move.id,
        }

        # Extract Data from First Line
        if line:
            vals["expense_account_id"] = line.account_id.id
            # Map Tax Invoice (Support both custom and standard reference)
            vals["tax_invoice_number"] = getattr(
                line, "tax_invoice_number", line.reference
            )
            vals["tax_invoice_date"] = getattr(line, "tax_invoice_date", line.date)

            # Map Taxes (Split VAT / WHT)
            # VAT > 0, WHT < 0 (General Logic)
            vat = line.tax_ids.filtered(lambda t: t.amount >= 0)[:1]
            wht = line.tax_ids.filtered(lambda t: t.amount < 0)[:1]
            if vat:
                vals["vat_tax_id"] = vat.id
            if wht:
                vals["wht_tax_id"] = wht.id

        if existing_log_no_move:
            existing_log_no_move.write(vals)
            return

        # Create New
        create_vals = {
            "date": sheet.accounting_date or fields.Date.today(),
            "transaction_type": "expense",
            "employee_id": sheet.employee_id.id,
            "description": f"Clear (Exp): {sheet.name}",
            "amount": sheet.total_amount,
            "journal_id": sheet.journal_id.id,
            "expense_sheet_id": sheet.id,
        }
        create_vals.update(vals)
        Log.create(create_vals)

    def action_pay_with_advance(self):
        """เปิด Wizard ให้เลือกใบ Advance ที่จะตัดยอด"""
        self.ensure_one()
        if self.state != "post":
            raise UserError(_("ต้อง Post รายการลงบัญชีก่อน ถึงจะตัดยอดเงินยืมได้"))

        return {
            "name": "ตัดยอดเงินยืม (Clear Advance)",
            "type": "ir.actions.act_window",
            "res_model": "advance.clearing.wizard",  # เดี๋ยวสร้าง Wizard นี้ด้านล่าง
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_expense_sheet_id": self.id,
                "default_employee_id": self.employee_id.id,
                "default_amount": self.total_amount,
            },
        }

    def action_open_advance_log(self):
        """ปุ่ม Smart Button วิ่งไปหา Log"""
        self.ensure_one()
        return {
            "name": "Advance Logbook",
            "type": "ir.actions.act_window",
            "res_model": "advance.cash.log",
            "view_mode": "list,form",
            "domain": [("expense_sheet_id", "=", self.id)],
            "context": {"create": False, "delete": False},
        }


class AdvanceClearingWizard(models.TransientModel):
    _name = "advance.clearing.wizard"
    _description = "Wizard เลือกใบยืมที่จะเคลียร์"

    expense_sheet_id = fields.Many2one("hr.expense.sheet", required=True)
    employee_id = fields.Many2one("hr.employee", string="พนักงาน", readonly=True)
    amount = fields.Float(string="ยอดที่จะเคลียร์", readonly=True)

    # ให้เลือกเฉพาะ Journal Advance (หรือเลือกบัญชี Advance)
    # แต่ใน Logbook เราเลือก Journal ดังนั้นเราให้เลือก Journal ที่มี Advance
    journal_id = fields.Many2one(
        "account.journal",
        string="ตัดจากวงเงิน/บัญชี",
        domain=[("type", "in", ["cash", "bank"])],
        required=True,
    )

    def action_confirm(self):
        self.ensure_one()
        sheet = self.expense_sheet_id

        # 1. Create Logbook Entry (Expense Type)
        create_vals = {
            "date": sheet.accounting_date or fields.Date.today(),
            "journal_id": self.journal_id.id,
            "transaction_type": "expense",
            "employee_id": self.employee_id.id,
            "description": f"Clear Advance: {sheet.name}",
            "amount": self.amount,
            "expense_sheet_id": sheet.id,
        }

        # Extract Tax/Invoice Data from First Line
        line = sheet.expense_line_ids[0] if sheet.expense_line_ids else False
        if line:
            create_vals["expense_account_id"] = line.account_id.id
            create_vals["tax_invoice_number"] = getattr(
                line, "tax_invoice_number", line.reference
            )
            create_vals["tax_invoice_date"] = getattr(
                line, "tax_invoice_date", line.date
            )
            vat = line.tax_ids.filtered(lambda t: t.amount >= 0)[:1]
            wht = line.tax_ids.filtered(lambda t: t.amount < 0)[:1]
            if vat:
                create_vals["vat_tax_id"] = vat.id
            if wht:
                create_vals["wht_tax_id"] = wht.id

        log = self.env["advance.cash.log"].create(create_vals)

        # 2. Register Payment to clear Expense Liability and reduce Advance Asset
        advance_account = self.journal_id.advance_account_id
        if not advance_account:
            raise UserError("Advance Account not found in Journal.")

        payable_lines = sheet.account_move_ids[0].line_ids.filtered(
            lambda l: l.account_type == "liability_payable"
            and l.credit > 0
            and not l.reconciled
        )
        if not payable_lines:
            raise UserError(
                f"No payable found for Expense {sheet.name} (maybe already paid)."
            )

        move = self.env["account.move"].create(
            {
                "journal_id": self.journal_id.id,
                "date": log.date,
                "ref": f"Clear Advance: {sheet.name}",
                "move_type": "entry",
                "expense_sheet_id": sheet.id,
                "line_ids": [
                    fields.Command.create(
                        {
                            "account_id": payable_lines[0].account_id.id,
                            "partner_id": self.employee_id.work_contact_id.id,
                            "name": f"Pay Expense: {sheet.name}",
                            "debit": self.amount,
                            "credit": 0.0,
                        }
                    ),
                    fields.Command.create(
                        {
                            "account_id": advance_account.id,
                            "name": "Deduct Advance",
                            "debit": 0.0,
                            "credit": self.amount,
                        }
                    ),
                ],
            }
        )
        move.action_post()

        # Reconcile
        (payable_lines + move.line_ids.filtered(lambda l: l.debit > 0)).reconcile()

        # Update Logbook
        log.write(
            {
                "state": "posted",
                "move_id": move.id,
            }
        )
