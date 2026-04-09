from odoo import Command, _, fields, models
from odoo.exceptions import UserError


class HrExpense(models.Model):
    _inherit = 'hr.expense'
    pass


class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'

    def action_pay_with_petty_cash(self):
        """
        Step 1: Open Wizard to let user select the Petty Cash Journal.
        """
        self.ensure_one()
        if self.state != 'post':
            raise UserError(_("Expense Report ต้องได้รับการอนุมัติ (Posted) ก่อน"))

        # Try to find a default journal to pre-fill
        default_journal_id = False
        if self.employee_journal_id and self.employee_journal_id.type == 'cash':
            default_journal_id = self.employee_journal_id.id
        elif self.payment_method_line_id and self.payment_method_line_id.journal_id.type == 'cash':
            default_journal_id = self.payment_method_line_id.journal_id.id
        else:
            petty = self.env['account.journal'].search([
                ('type', '=', 'cash'),
                ('company_id', '=', self.company_id.id),
                ('name', 'ilike', 'Petty')
            ], limit=1)
            if not petty:
                petty = self.env['account.journal'].search([
                    ('type', '=', 'cash'),
                    ('company_id', '=', self.company_id.id)
                ], limit=1)
            if petty:
                default_journal_id = petty.id

        return {
            'name': _("Pay with Petty Cash"),
            'type': 'ir.actions.act_window',
            'res_model': 'petty.cash.payment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_expense_sheet_id': self.id,
                'default_journal_id': default_journal_id
            }
        }

    def _action_pay_with_petty_cash_process(self, petty_journal):
        """
        Step 2: Actual Process (Called by Wizard)
        Creates account.move directly to ensure immediate 'Paid' status.
        """
        self.ensure_one()

        moves_to_pay = self.account_move_ids.filtered(
            lambda m: m.state == 'posted' and m.amount_residual > 0 and m.move_type in ('in_invoice', 'entry')
        )

        if not moves_to_pay:
            raise UserError(_("ไม่พบยอดค้างชำระสำหรับเอกสารนี้"))

        # Balance Check
        default_account = petty_journal.default_account_id
        if not default_account:
             raise UserError(_("สมุดรายวัน %s ไม่ได้ระบุ Default Account") % petty_journal.name)

        domain = [('account_id', '=', default_account.id), ('parent_state', '=', 'posted')]
        result = self.env['account.move.line'].read_group(domain, ['balance'], ['account_id'])
        current_balance = result[0]['balance'] if result else 0.0
        amount_to_pay = sum(moves_to_pay.mapped('amount_residual'))

        if current_balance < amount_to_pay:
             raise UserError(
                _("ยอดเงินสดย่อยไม่พอ!\n"
                  "สมุดรายวัน: %s\n"
                  "ยอดยกมา: %.2f\n"
                  "ยอดที่ต้องจ่าย: %.2f") % (petty_journal.name, current_balance, amount_to_pay)
             )

        for move in moves_to_pay:
            amount = move.amount_residual

            # Find Payable line in the Vendor Bill
            payable_line = move.line_ids.filtered(
                lambda line: line.account_type == 'liability_payable' and not line.reconciled
            )[:1]

            if not payable_line:
                continue

            # --- Create Journal Entry (Direct Payment) ---
            move_vals = {
                'journal_id': petty_journal.id,
                'date': fields.Date.context_today(self),
                'ref': f"Pay Expense: {self.name}",
                'move_type': 'entry',
                'expense_sheet_id': self.id,
                'line_ids': [
                    Command.create({
                        'account_id': payable_line.account_id.id,
                        'partner_id': move.partner_id.id,
                        'name': f"Pay {move.name}",
                        'debit': amount,
                        'credit': 0.0,
                    }),
                    Command.create({
                        'account_id': default_account.id, # Direct to Cash Account
                        'name': "Payment with Petty Cash",
                        'debit': 0.0,
                        'credit': amount,
                    }),
                ]
            }

            payment_move = self.env['account.move'].create(move_vals)
            payment_move.action_post()

            # --- Reconcile ---
            payment_dr_line = payment_move.line_ids.filtered(
                lambda line: line.account_id == payable_line.account_id and line.debit > 0
            )
            (payable_line + payment_dr_line).reconcile()

            # ==========================================
            # [FIX] Find Expense Account & Analytics from Bill
            # ==========================================
            expense_acc_id = False
            analytic_distribution = False
            if move.invoice_line_ids:
                line = move.invoice_line_ids[0]
                expense_acc_id = line.account_id.id
                analytic_distribution = line.analytic_distribution

            # --- Create Petty Cash Log ---
            log_vals = {
                'date': payment_move.date,
                'company_id': payment_move.company_id.id,
                'journal_id': petty_journal.id,
                'transaction_type': 'out',
                'amount': amount,
                'description': "Expense Payment: " + (self.name or ''),
                'expense_sheet_id': self.id,
                'expense_account_id': expense_acc_id,
                'analytic_distribution': analytic_distribution,
                'state': 'posted',
                'move_id': payment_move.id,
                'partner_id': move.partner_id.id,
            }

            # Tax Logic Extraction
            tax_lines = move.line_ids.filtered(lambda line: line.tax_line_id)
            base_lines = move.line_ids.filtered(lambda line: line.tax_ids)

            # Try to find a group tax or just the first tax
            tax_ids = tax_lines.mapped('tax_line_id')
            if tax_ids:
                log_vals['vat_tax_id'] = tax_ids[0].id

            if base_lines:
                total_base = sum(base_lines.mapped('balance'))
                log_vals['amount'] = total_base
            else:
                log_vals['amount'] = amount

            # Thai Tax Invoice Info
            expense_ids = move.line_ids.mapped('expense_id')
            hr_tax_number = False
            hr_tax_date = False

            for exp in expense_ids:
                if getattr(exp, 'tax_number', False):
                     hr_tax_number = exp.tax_number
                     hr_tax_date = exp.tax_date
                     break

            if hr_tax_number:
                log_vals['tax_invoice_number'] = hr_tax_number
                log_vals['tax_invoice_date'] = hr_tax_date
            elif hasattr(move, 'tax_invoice_ids') and move.tax_invoice_ids:
                tax_inv = move.tax_invoice_ids[:1]
                log_vals['tax_invoice_number'] = tax_inv.tax_invoice_number
                log_vals['tax_invoice_date'] = tax_inv.tax_invoice_date

            # Create Log
            self.env['petty.cash.log'].create(log_vals)
