from odoo import Command, _, api, models
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    def _get_base_payment_amount_for_wht(self):
        """Return gross payment amount before WHT deduction.

        Use core computed amount-by-default so repeated onchange/compute calls
        stay idempotent (no double deduction).
        """
        self.ensure_one()

        # If the user has manually frozen the amount, that is the undisputed base amount
        if getattr(self, 'custom_user_amount', 0.0) and getattr(self, 'custom_user_currency_id', False) == self.currency_id:
            return self.custom_user_amount

        gross_candidate = (self.amount or 0.0) + (self.payment_difference or 0.0)
        if self.currency_id and not self.currency_id.is_zero(gross_candidate) and gross_candidate > 0.0:
            return gross_candidate
        if self.journal_id and self.currency_id and self.payment_date:
            total_amount_values = self._get_total_amounts_to_pay(self.batches)
            return total_amount_values["amount_by_default"]
        return self.amount

    def _is_wht_deduction_line(self, deduction):
        if "wht_tax_id" not in deduction._fields:
            return False
        return bool(deduction.wht_tax_id)

    def _prepare_manual_deduction_command(self, deduction):
        values = {
            "name": deduction.name,
            "account_id": deduction.account_id.id,
            "amount": deduction.amount,
            "is_open": deduction.is_open,
        }
        if "analytic_distribution" in deduction._fields:
            values["analytic_distribution"] = deduction.analytic_distribution or {}
        if "partner_id" in deduction._fields and deduction.partner_id:
            values["partner_id"] = deduction.partner_id.id
        if "wht_tax_id" in deduction._fields:
            values["wht_tax_id"] = False
        if "wht_amount_base" in deduction._fields:
            values["wht_amount_base"] = 0.0
        return Command.create(values)

    def _sync_multi_deduction_balance(self):
        self.ensure_one()
        if not self.deduction_ids:
            return
        # Do not silently rewrite user-entered manual deductions (e.g. bank fee).
        # Auto-balance is only for full auto-WHT mode.
        manual_deductions = self.deduction_ids.filtered(
            lambda d: not self._is_wht_deduction_line(d)
        )
        if manual_deductions:
            return
        expected = self.payment_difference
        current = sum(self.deduction_ids.mapped("amount"))
        if self.currency_id.compare_amounts(expected, current) == 0:
            return
        target = self.deduction_ids.filtered(lambda d: not d.is_open)[-1:] or self.deduction_ids[-1:]
        if target:
            target.with_context(skip_wht_deduct=True).write(
                {"amount": target.amount + (expected - current)}
            )

    @api.constrains("deduction_ids", "payment_difference_handling")
    def _check_deduction_amount(self):
        # Internal auto-fill writes run before all computed monetary fields are stable.
        # Skip validation there; normal user validation still runs on create payment.
        if self.env.context.get("skip_wht_deduct"):
            return
        for rec in self:
            if rec.payment_difference_handling != "reconcile_multi_deduct":
                continue
            # Allow unbalanced deductions if manual FX rate is used
            # (as it will auto-balance with FX write-off line later)
            if getattr(rec, 'manual_currency_rate_active', False) and getattr(rec, 'manual_currency_rate', 0.0):
                continue
            total_deduction = sum(rec.deduction_ids.mapped("amount"))
            if rec.currency_id.compare_amounts(rec.payment_difference, total_deduction) != 0:
                raise UserError(
                    _("The total deduction should be %s") % rec.payment_difference
                )

    @api.depends("early_payment_discount_mode")
    def _compute_payment_difference_handling(self):
        res = super()._compute_payment_difference_handling()
        if self.env.context.get("skip_wht_deduct"):
            return res
        for wizard in self:
            wht_lines = wizard._get_wht_source_lines()
            if not wht_lines:
                continue
            if hasattr(wht_lines, "_prepare_multi_wht_deduction_list"):
                deduction_list, _amount_deduct = wht_lines._prepare_multi_wht_deduction_list(
                    wizard.payment_date,
                    wizard.currency_id,
                )
            else:
                deduction_list, _amount_deduct = wht_lines._prepare_deduction_list(
                    wizard.payment_date,
                    wizard.currency_id,
                )
            if len(deduction_list) > 1 and wizard.payment_difference_handling == "open":
                wizard.payment_difference_handling = "reconcile_multi_deduct"
        return res

    def _get_wht_source_lines(self):
        self.ensure_one()
        model = self.env.context.get("active_model")
        active_ids = self.env.context.get("active_ids", [])
        if model == "account.move":
            move_lines = self.env["account.move"].browse(active_ids).mapped("invoice_line_ids")
        elif model == "account.move.line":
            move_lines = self.env["account.move.line"].browse(active_ids)
            if not move_lines.filtered(lambda l: l.wht_tax_id or l.wht_tax_ids):
                move_lines = move_lines.mapped("move_id").mapped("invoice_line_ids")
        else:
            move_lines = self.env["account.move.line"]
        return move_lines.filtered(lambda l: l.wht_tax_id or l.wht_tax_ids)

    def _auto_apply_wht_from_lines(self):
        self.ensure_one()
        if self.env.context.get("skip_wht_deduct"):
            return

        wht_lines = self._get_wht_source_lines()
        if not wht_lines:
            return

        if hasattr(wht_lines, "_prepare_multi_wht_deduction_list"):
            deduction_list, amount_deduct = wht_lines._prepare_multi_wht_deduction_list(
                self.payment_date,
                self.currency_id,
            )
        else:
            deduction_list, amount_deduct = wht_lines._prepare_deduction_list(
                self.payment_date,
                self.currency_id,
            )
        if not deduction_list:
            return

        base_amount = self._get_base_payment_amount_for_wht()
        amount_after_deduct = base_amount - amount_deduct
        payment_amount = amount_after_deduct if amount_after_deduct > 0 else 0.0

        existing_manual_deductions = self.deduction_ids.filtered(
            lambda d: not self._is_wht_deduction_line(d)
        )

        # Single effective WHT (same tax grouped by partner) -> normal reconcile write-off
        if len(deduction_list) == 1 and not existing_manual_deductions:
            deduction = deduction_list[0]
            wht_tax = self.env["account.withholding.tax"].browse(deduction["wht_tax_id"])
            values = {
                "amount": payment_amount,
                "payment_difference_handling": "reconcile",
                "wht_tax_id": wht_tax.id,
                "wht_amount_base": deduction["wht_amount_base"],
                "writeoff_account_id": wht_tax.account_id.id,
                "writeoff_label": wht_tax.display_name,
            }
            if "deduction_ids" in self._fields:
                values["deduction_ids"] = [Command.clear()]
            self.with_context(skip_wht_deduct=True).write(values)
            return

        # Multiple WHT types -> multi deduction lines with account from each WHT config
        wizard_values = {
            # Keep "open" during internal update to avoid premature validation.
            "payment_difference_handling": "open",
            "wht_tax_id": False,
            "wht_amount_base": 0.0,
            "writeoff_account_id": False,
            "writeoff_label": False,
        }
        manual_commands = [
            self._prepare_manual_deduction_command(deduction)
            for deduction in existing_manual_deductions
        ]
        deduction_commands = []
        analytic = self.deduct_analytic_distribution if "deduct_analytic_distribution" in self._fields else {}
        for deduction in deduction_list:
            deduction_values = dict(deduction)
            if "analytic_distribution" in self.env["account.payment.deduction"]._fields:
                deduction_values["analytic_distribution"] = analytic
            deduction_commands.append(Command.create(deduction_values))
        if "deduction_ids" in self._fields:
            wizard_values["deduction_ids"] = [Command.clear()] + manual_commands + deduction_commands
        self.with_context(skip_wht_deduct=True).write(wizard_values)

        total_deduction = sum(self.deduction_ids.filtered(lambda d: not d.is_open).mapped("amount"))
        payment_amount = base_amount - total_deduction
        if payment_amount < 0:
            payment_amount = 0.0

        self.with_context(skip_wht_deduct=True).write(
            {
                "amount": payment_amount,
            }
        )
        self._sync_multi_deduction_balance()
        self.with_context(skip_wht_deduct=True).write(
            {
                "payment_difference_handling": "reconcile_multi_deduct",
            }
        )
        self._sync_multi_deduction_balance()

    @api.onchange("currency_id")
    def _onchange_currency_id(self):
        res = super()._onchange_currency_id()
        for wizard in self:
            wizard._auto_apply_wht_from_lines()
        return res

    @api.onchange("payment_date")
    def _onchange_payment_date(self):
        res = super()._onchange_payment_date()
        for wizard in self:
            wizard._auto_apply_wht_from_lines()
        return res

    @api.onchange("journal_id", "payment_method_line_id")
    def _onchange_wht_payment_context(self):
        parent = getattr(super(), "_onchange_wht_payment_context", None)
        res = parent() if parent else None
        for wizard in self:
            wizard._auto_apply_wht_from_lines()
        return res

    @api.onchange("manual_currency_rate", "manual_currency_rate_active")
    def _onchange_manual_currency_rate_fix(self):
        parent = getattr(super(), "_onchange_manual_currency_rate_fix", None)
        res = parent() if parent else None
        for wizard in self:
            wizard._auto_apply_wht_from_lines()
        return res

    @api.depends(
        "can_edit_wizard",
        "source_amount",
        "source_amount_currency",
        "source_currency_id",
        "company_id",
        "currency_id",
        "payment_date",
        "journal_id",
        "payment_method_line_id",
        "installments_mode",
        "manual_currency_rate",
        "manual_currency_rate_active",
    )
    def _compute_amount(self):
        res = super()._compute_amount()
        for wizard in self:
            if not wizard.journal_id or not wizard.currency_id:
                continue
            wizard._auto_apply_wht_from_lines()
        return res
