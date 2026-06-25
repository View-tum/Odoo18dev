from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    def _get_wht_source_account_lines(self):
        self.ensure_one()
        source_lines = self.line_ids
        if not source_lines and self.batches:
            for batch in self.batches:
                source_lines |= batch["lines"]
        if not source_lines and "allocation_line_ids" in self._fields:
            source_lines |= self.allocation_line_ids.mapped("move_line_id")

        if source_lines:
            return source_lines

        model = self.env.context.get("active_model")
        active_ids = self.env.context.get("active_ids", [])
        if model == "account.move":
            return self.env["account.move"].browse(active_ids).line_ids
        if model == "account.move.line":
            return self.env["account.move.line"].browse(active_ids)
        return self.env["account.move.line"]

    def _get_wht_fallback_residual_amount(self):
        """Get a stable source residual when source move lines are temporarily unavailable.

        In payment register recomputes (e.g. journal onchange), context-based source lines can
        be missing for a transient moment. We must not use existing deduction totals in this
        fallback to avoid compounding the payment base.
        """
        self.ensure_one()
        payment_date = self.payment_date or fields.Date.context_today(self)

        source_amount_currency = abs(getattr(self, "source_amount_currency", 0.0) or 0.0)
        source_amount = abs(getattr(self, "source_amount", 0.0) or 0.0)
        source_currency = getattr(self, "source_currency_id", False)

        if source_amount_currency and source_currency:
            if source_currency == self.currency_id:
                return source_amount_currency
            return self._convert_with_manual_rate(
                source_amount_currency,
                source_currency,
                self.currency_id,
            )

        if source_amount:
            if self.currency_id == self.company_id.currency_id:
                return source_amount
            return self._convert_with_manual_rate(
                source_amount,
                self.company_id.currency_id,
                self.currency_id,
            )

        # Last-resort fallback: amount + payment_difference already equals residual in core.
        # Do not add deductions here, otherwise the base compounds on every onchange.
        return abs((self.amount or 0.0) + (self.payment_difference or 0.0))

    def _get_wht_source_moves(self):
        self.ensure_one()
        source_lines = self._get_wht_source_account_lines()
        if source_lines:
            return source_lines.move_id

        model = self.env.context.get("active_model")
        active_ids = self.env.context.get("active_ids", [])
        if model == "account.move":
            return self.env["account.move"].browse(active_ids)
        if model == "account.move.line":
            return self.env["account.move.line"].browse(active_ids).move_id
        return self.env["account.move"]

    def _get_base_payment_amount_for_wht(self):
        """
        Calculate the stable residual amount from source lines to avoid compounding loops.
        Returns (total_residual, total_original_payable) in the wizard's currency.
        """
        self.ensure_one()
        source_lines = self._get_wht_source_account_lines()

        if not source_lines:
            base = self._get_wht_fallback_residual_amount()
            return base, base

        total_residual = 0.0
        total_original_gross = 0.0
        payment_date = self.payment_date or fields.Date.context_today(self)

        # 1. Total Residual (amount still to be paid)
        for line in source_lines:
            line_currency = line.currency_id or line.company_currency_id
            if line_currency == self.currency_id:
                line_res = (
                    abs(line.amount_residual_currency)
                    if line.currency_id
                    else abs(line.amount_residual)
                )
            else:
                source_amount = (
                    abs(line.amount_residual_currency)
                    if line.currency_id
                    else abs(line.amount_residual)
                )
                line_res = self._convert_with_manual_rate(
                    source_amount,
                    line_currency,
                    self.currency_id,
                )
            total_residual += line_res

        moves = self._get_wht_source_moves()
        for move in moves:
            move_gross = abs(move.amount_total)
            total_original_gross += self._convert_with_manual_rate(
                move_gross,
                move.currency_id,
                self.currency_id,
            )

        return total_residual, total_original_gross

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
        full_residual, _original = self._get_base_payment_amount_for_wht()
        expected = full_residual - self.amount
        current = sum(self.deduction_ids.mapped("amount"))
        if self.currency_id.compare_amounts(expected, current) == 0:
            return
        # Adjust the last non-WHT line if possible, otherwise any non-WHT line
        target = (
            self.deduction_ids.filtered(
                lambda d: not d.is_open and not self._is_wht_deduction_line(d)
            )[-1:]
            or self.deduction_ids.filtered(lambda d: not self._is_wht_deduction_line(d))
            [-1:]
        )
        if target:
            target.update({"amount": target.amount + (expected - current)})

    @api.constrains("deduction_ids", "payment_difference_handling")
    def _check_deduction_amount(self):
        if self.env.context.get("skip_wht_deduct") or self.env.context.get("in_wht_sync"):
            return
        for rec in self:
            if rec.payment_difference_handling != "reconcile_multi_deduct":
                continue
            if rec._get_wht_source_lines() and not rec.deduction_ids:
                continue
            if getattr(rec, 'manual_currency_rate_active', False) and getattr(rec, 'manual_currency_rate', 0.0):
                continue
            total_deduction = sum(rec.deduction_ids.mapped("amount"))
            full_residual, _original = rec._get_base_payment_amount_for_wht()
            expected_diff = full_residual - rec.amount
            if rec.currency_id.compare_amounts(expected_diff, total_deduction) != 0:
                raise UserError(
                    _("The total deduction should be %s") % expected_diff
                )

    @api.depends("early_payment_discount_mode")
    def _compute_payment_difference_handling(self):
        res = super()._compute_payment_difference_handling()
        if self.env.context.get("skip_wht_deduct"):
            return res
        return res

    def _get_wht_source_lines(self):
        self.ensure_one()
        active_line_ids = self.env.context.get("active_ids", [])
        active_model = self.env.context.get("active_model")
        invoice_lines = self.env["account.move.line"]

        # If the wizard was launched directly from invoice lines, keep them.
        if active_model == "account.move.line" and active_line_ids:
            active_lines = self.env["account.move.line"].browse(active_line_ids)
            invoice_lines |= active_lines.filtered(lambda line: line.display_type == "product")

        moves = self._get_wht_source_moves()
        invoice_lines |= moves.mapped("invoice_line_ids").filtered(
            lambda line: line.display_type == "product"
        )

        return invoice_lines.filtered(lambda line: line.wht_tax_id or line.wht_tax_ids)

    def _get_existing_wht_amount(self):
        self.ensure_one()
        if "deduction_ids" not in self._fields:
            return 0.0
        return sum(
            self.deduction_ids.filtered(self._is_wht_deduction_line).mapped("amount")
        )

    def _has_custom_user_amount_for_wht(self):
        self.ensure_one()
        return bool(getattr(self, "custom_user_amount", False))

    def _allow_custom_user_amount_for_wht(self):
        self.ensure_one()
        # "Mark invoice as fully paid" modes must stay balanced against the
        # invoice residual. A journal onchange can make core mark the transient
        # amount as custom even though the user did not manually key it.
        return (
            self._has_custom_user_amount_for_wht()
            and self.payment_difference_handling == "open"
        )

    def _is_auto_difference_deduction_line(self, deduction):
        company = self.company_id
        auto_account = getattr(company, "auto_diff_account_id", False)
        if not auto_account:
            return False
        return deduction.account_id == auto_account

    def _is_preservable_manual_deduction(self, deduction):
        if self._is_wht_deduction_line(deduction):
            return False
        if self._is_auto_difference_deduction_line(deduction):
            return False
        return bool(deduction.account_id or deduction.name or deduction.amount or deduction.is_open)

    def _auto_apply_wht_from_lines(self):
        self.ensure_one()
        if self.env.context.get("skip_wht_deduct") or self.env.context.get("in_wht_sync"):
            return

        wht_lines = self._get_wht_source_lines()
        if not wht_lines:
            return

        self = self.with_context(in_wht_sync=True)

        batch_residual, total_original_payable = self._get_base_payment_amount_for_wht()
        if total_original_payable <= 0:
            return

        residual_ratio = min(batch_residual / total_original_payable, 1.0)

        # Calculate Full WHT for the residual amount
        if hasattr(wht_lines, "_prepare_multi_wht_deduction_list"):
            _full_list, full_wht_for_residual = wht_lines._prepare_multi_wht_deduction_list(
                self.payment_date,
                self.currency_id,
                pay_ratio=residual_ratio,
            )
        else:
            _full_list, full_wht_for_residual = wht_lines._prepare_deduction_list(
                self.payment_date,
                self.currency_id,
            )
            full_wht_for_residual *= residual_ratio

        # Only a real user-entered amount should prorate WHT. Journal/payment onchange
        # can temporarily alter self.amount; treating that as partial payment compounds
        # payment difference and scales WHT incorrectly.
        total_net_expected_full = batch_residual - full_wht_for_residual
        existing_wht_amount = self._get_existing_wht_amount()
        is_custom_user_amount = self._allow_custom_user_amount_for_wht()
        if not is_custom_user_amount and self._has_custom_user_amount_for_wht():
            self.custom_user_amount = False
            self.custom_user_currency_id = False

        pay_ratio_of_residual = 1.0
        if is_custom_user_amount and total_net_expected_full > 0:
            if self.currency_id.compare_amounts(self.amount, total_net_expected_full) != 0:
                # If amount is exactly total_residual (no WHT yet), treat as full payment intent
                if self.currency_id.compare_amounts(self.amount, batch_residual) == 0:
                    pay_ratio_of_residual = 1.0
                elif self.currency_id.compare_amounts(
                    self.amount + existing_wht_amount, batch_residual
                ) == 0:
                    pay_ratio_of_residual = 1.0
                else:
                    pay_ratio_of_residual = min(max(self.amount / total_net_expected_full, 0.0), 1.0)

        final_pay_ratio = residual_ratio * pay_ratio_of_residual

        # Get final deduction list
        if hasattr(wht_lines, "_prepare_multi_wht_deduction_list"):
            deduction_list, amount_deduct = wht_lines._prepare_multi_wht_deduction_list(
                self.payment_date,
                self.currency_id,
                pay_ratio=final_pay_ratio,
            )
        else:
            deduction_list, amount_deduct = wht_lines._prepare_deduction_list(
                self.payment_date,
                self.currency_id,
            )
            for d in deduction_list:
                d['amount'] *= final_pay_ratio
                d['wht_amount_base'] *= final_pay_ratio
            amount_deduct *= final_pay_ratio

        if not deduction_list:
            return

        # Identification and comparison
        existing_manual = self.deduction_ids.filtered(self._is_preservable_manual_deduction)
        existing_wht = self.deduction_ids.filtered(self._is_wht_deduction_line)
        manual_deduct_amount = sum(existing_manual.mapped("amount"))

        needs_update = False
        if len(existing_wht) != len(deduction_list):
            needs_update = True
        else:
            # Sort both to compare pairs
            sorted_existing = sorted(existing_wht, key=lambda d: (d.wht_tax_id.id, d.partner_id.id))
            sorted_new = sorted(deduction_list, key=lambda d: (d.get("wht_tax_id"), d.get("partner_id")))
            for e, n in zip(sorted_existing, sorted_new):
                if (
                    e.wht_tax_id.id != n.get("wht_tax_id")
                    or self.currency_id.compare_amounts(e.amount, n.get("amount")) != 0
                    or self.currency_id.compare_amounts(
                        e.wht_amount_base,
                        n.get("wht_amount_base"),
                    ) != 0
                ):
                    needs_update = True
                    break

        # Handling mode persistence
        current_handling = self.payment_difference_handling
        is_multi_wht = len(deduction_list) > 1

        target_handling = current_handling
        if is_multi_wht and not is_custom_user_amount:
            target_handling = 'reconcile_multi_deduct'
        elif not is_custom_user_amount and current_handling not in ('reconcile_multi_deduct', 'reconcile'):
            # Only auto-switch to reconcile if it's currently 'open' and we have WHT
            target_handling = 'reconcile'

        if current_handling != target_handling:
            needs_update = True

        if not needs_update:
            # Just ensure amount is in sync if it was a full payment intent
            expected_amount = (
                (batch_residual * pay_ratio_of_residual)
                - amount_deduct
                - manual_deduct_amount
            )
            if (
                self.currency_id.compare_amounts(self.amount, expected_amount) != 0
                and (not is_custom_user_amount or pay_ratio_of_residual == 1.0)
            ):
                self.amount = max(expected_amount, 0.0)
            return

        # Prepare update values
        target_payment_amount = max(
            (batch_residual * pay_ratio_of_residual)
            - amount_deduct
            - manual_deduct_amount,
            0.0,
        )
        wizard_values = {
            "amount": target_payment_amount,
            "payment_difference_handling": target_handling,
        }

        if target_handling == 'reconcile' and not is_multi_wht:
            deduction = deduction_list[0]
            wht_tax = self.env["account.withholding.tax"].browse(deduction["wht_tax_id"])
            wizard_values.update({
                "wht_tax_id": wht_tax.id,
                "wht_amount_base": deduction["wht_amount_base"],
                "writeoff_account_id": wht_tax.account_id.id,
                "writeoff_label": wht_tax.display_name,
            })
            if "deduction_ids" in self._fields:
                wizard_values["deduction_ids"] = [Command.clear()]
        else:
            wizard_values.update({
                "wht_tax_id": False,
                "wht_amount_base": 0.0,
                "writeoff_account_id": False,
                "writeoff_label": False,
            })
            manual_cmds = [self._prepare_manual_deduction_command(d) for d in existing_manual]
            analytic = getattr(self, 'deduct_analytic_distribution', {})
            wht_cmds = []
            for d in deduction_list:
                d_vals = dict(d)
                if "analytic_distribution" in self.env["account.payment.deduction"]._fields:
                    d_vals["analytic_distribution"] = analytic
                wht_cmds.append(Command.create(d_vals))

            if "deduction_ids" in self._fields:
                wizard_values["deduction_ids"] = [Command.clear()] + manual_cmds + wht_cmds

        self.update(wizard_values)

        # Final amount adjustment for full payment intent
        if pay_ratio_of_residual == 1.0:
            total_deduct_all = sum(self.deduction_ids.mapped("amount"))
            final_amount = max((batch_residual * pay_ratio_of_residual) - total_deduct_all, 0.0)
            if self.currency_id.compare_amounts(self.amount, final_amount) != 0:
                self.amount = final_amount

        self._sync_multi_deduction_balance()

    @api.onchange("payment_difference_handling")
    def _onchange_payment_difference_handling(self):
        if self.env.context.get("in_wht_sync"):
            return
        if self.payment_difference_handling in ("reconcile_multi_deduct", "reconcile"):
            self._auto_apply_wht_from_lines()

    @api.onchange("currency_id", "payment_date", "journal_id", "payment_method_line_id")
    def _onchange_wht_auto_trigger(self):
        for wizard in self:
            wizard._auto_apply_wht_from_lines()

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
        super()._compute_amount()
        for wizard in self:
            if wizard.journal_id and wizard.currency_id:
                wizard._auto_apply_wht_from_lines()
