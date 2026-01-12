from odoo import models, fields, _
from odoo.exceptions import UserError


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    is_foc = fields.Boolean(string="Free of Charge")
    foc_price_unit = fields.Monetary(
        string="FOC Unit Price",
        currency_field="currency_id",
        help="Internal valuation unit price for FOC lines carried from the sale order.",
    )


class AccountMove(models.Model):
    _inherit = "account.move"

    def _stock_account_prepare_anglo_saxon_out_lines_vals(self):
        # 1) Let Odoo compute all default COGS lines
        lines_vals_list = super()._stock_account_prepare_anglo_saxon_out_lines_vals()

        # 2) Only consider invoices (no receipts)
        foc_moves = self.filtered(lambda m: m.is_invoice(include_receipts=False))
        if not foc_moves:
            return lines_vals_list

        # 3) Map move_id -> your FOC expense account (if set) only when FOC lines exist
        foc_expense_by_move = {}
        for move in foc_moves:
            company = move.company_id
            has_foc = any(move.invoice_line_ids.filtered("is_foc"))
            if not has_foc:
                continue
            debit_account = company.foc_cogs_adjust_account_id
            if debit_account:
                foc_expense_by_move[move.id] = debit_account.id
            else:
                # 🔴 Show warning when config is missing
                raise UserError(_(
                    "Please fill the COGS debit account for FOC in the Company Settings(Settings -> User & Companies -> Companies)" ""
                    "for company '%s'."
                ) % (company.display_name,))

        if not foc_expense_by_move:
            return lines_vals_list

        aml_model = self.env['account.move.line']

        # 4) Post-process only NON-FOC expense lines
        for vals in lines_vals_list:
            move_id = vals.get('move_id')
            if not move_id or move_id not in foc_expense_by_move:
                continue
            if vals.get('display_type') != 'cogs':
                continue

            # Expense side: price_unit < 0 (Odoo pattern)
            if vals.get('price_unit', 0.0) >= 0.0:
                continue

            origin_id = vals.get('cogs_origin_id')
            if not origin_id:
                continue

            origin_line = aml_model.browse(origin_id)

            # 🔴 IMPORTANT: adjust this condition to your real FOC logic
            # e.g. a boolean field on the invoice line: origin_line.is_foc
            # We want ONLY non-FOC lines → skip if FOC.
            if getattr(origin_line, 'is_foc', False):
                continue

            # Replace expense account ONLY for non-FOC lines
            vals['account_id'] = foc_expense_by_move[move_id]

        return lines_vals_list
