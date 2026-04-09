from collections import defaultdict
from copy import deepcopy

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_round
from odoo.tools.misc import format_date


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    wht_tax_ids = fields.Many2many(
        comodel_name="account.withholding.tax",
        relation="account_move_line_wht_tax_rel",
        column1="move_line_id",
        column2="wht_tax_id",
        string="WHT",
        check_company=True,
        help="Allow selecting more than one withholding tax on a single invoice line.",
    )

    @api.onchange("wht_tax_id")
    def _onchange_wht_tax_id_fill_multi(self):
        for line in self:
            if line.wht_tax_id and not line.wht_tax_ids:
                line.wht_tax_ids = [Command.set([line.wht_tax_id.id])]

    @api.onchange("wht_tax_ids")
    def _onchange_wht_tax_ids_sync_single(self):
        for line in self:
            line.wht_tax_id = line.wht_tax_ids[:1] or False

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        if not self.env.context.get("skip_wht_multi_sync"):
            lines._sync_wht_fields()
        return lines

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get("skip_wht_multi_sync") and {
            "wht_tax_id",
            "wht_tax_ids",
        } & set(vals):
            self._sync_wht_fields()
        return res

    def _sync_wht_fields(self):
        for line in self:
            first_wht = line.wht_tax_ids[:1]
            if first_wht and line.wht_tax_id != first_wht:
                super(
                    AccountMoveLine, line.with_context(skip_wht_multi_sync=True)
                ).write({"wht_tax_id": first_wht.id})
            elif not first_wht and line.wht_tax_id:
                super(
                    AccountMoveLine, line.with_context(skip_wht_multi_sync=True)
                ).write({"wht_tax_ids": [Command.set([line.wht_tax_id.id])]})

    def _get_effective_wht_taxes(self):
        self.ensure_one()
        return self.wht_tax_ids or self.wht_tax_id

    def _prepare_multi_wht_deduction_list(self, date, currency):
        deductions = []
        amount_deduct = 0.0

        grouped_lines = defaultdict(lambda: self.env["account.move.line"])
        for line in self:
            taxes = line._get_effective_wht_taxes()
            if not taxes:
                continue
            partner = line.partner_id or line.move_id.partner_id
            for wht_tax in taxes:
                grouped_lines[(wht_tax.id, partner.id)] |= line

        for (wht_tax_id, partner_id), move_lines in grouped_lines.items():
            wht_tax = self.env["account.withholding.tax"].browse(wht_tax_id)
            amount_base, amount_wht = move_lines._get_wht_amount_for_tax(
                wht_tax,
                currency,
                date,
                partner_id,
            )
            amount_wht = float_round(amount_wht, precision_rounding=currency.rounding)
            amount_deduct += amount_wht
            deductions.append(
                {
                    "partner_id": partner_id,
                    "wht_amount_base": amount_base,
                    "wht_tax_id": wht_tax.id,
                    "account_id": wht_tax.account_id.id,
                    "name": wht_tax.display_name,
                    "amount": amount_wht,
                }
            )
        return (deductions, amount_deduct)

    def _get_wht_amount_for_tax(self, wht_tax, currency, date, partner_id):
        if not self:
            return (0.0, 0.0)

        amount_base = sum(line.amount_currency or line.price_subtotal for line in self)
        if wht_tax.is_pit:
            ref_line = self[0]
            company = ref_line.company_id
            partner = self.env["res.partner"].browse(partner_id)
            amount_base = ref_line.move_id.currency_id._convert(
                amount_base,
                currency,
                company,
                date,
            )
            effective_pit = wht_tax.with_context(pit_date=date).pit_id
            if not effective_pit:
                raise UserError(
                    self.env._("No effective PIT rate for date %s")
                    % format_date(self.env, date)
                )
            amount_wht = effective_pit._compute_expected_wht(
                partner,
                amount_base,
                pit_date=date,
                currency=currency,
                company=company,
            )
        else:
            amount_wht = amount_base * (wht_tax.amount / 100)
        return (amount_base, amount_wht)


class AccountMove(models.Model):
    _inherit = "account.move"

    def _post(self, soft=True):
        moves = super()._post(soft=soft)
        payments = moves.mapped("origin_payment_id").filtered(
            lambda p: p and p.payment_type == "outbound"
        )
        for payment in payments:
            if payment.wht_cert_ids:
                continue
            if payment.state == "canceled":
                continue
            if not payment.wht_move_ids:
                continue
            if payment.wht_move_ids.filtered(
                lambda move: not move.wht_cert_income_type
            ):
                continue
            payment.create_wht_cert()
        return moves

    @api.depends_context("lang")
    @api.depends(
        "invoice_line_ids.currency_rate",
        "invoice_line_ids.tax_base_amount",
        "invoice_line_ids.tax_line_id",
        "invoice_line_ids.price_total",
        "invoice_line_ids.price_subtotal",
        "invoice_line_ids.wht_tax_id",
        "invoice_line_ids.wht_tax_ids",
        "invoice_payment_term_id",
        "partner_id",
        "currency_id",
    )
    def _compute_tax_totals(self):
        super()._compute_tax_totals()
        for move in self:
            if not move.tax_totals or not move.is_invoice(include_receipts=True):
                continue

            preview_lines = move.invoice_line_ids.filtered(
                lambda l: l.display_type == "product"
                and (l.wht_tax_ids or l.wht_tax_id)
            )
            if not preview_lines:
                continue

            payment_date = move.invoice_date or move.date or fields.Date.context_today(move)
            deduction_list, _amount_deduct = preview_lines._prepare_multi_wht_deduction_list(
                payment_date,
                move.currency_id,
            )
            if not deduction_list:
                continue

            tax_totals = deepcopy(move.tax_totals)
            subtotals = tax_totals.get("subtotals") or []
            if not subtotals:
                subtotals = [
                    {
                        "name": _("Untaxed Amount"),
                        "tax_groups": [],
                        "tax_amount_currency": 0.0,
                        "tax_amount": 0.0,
                        "base_amount_currency": tax_totals.get(
                            "base_amount_currency", 0.0
                        ),
                        "base_amount": tax_totals.get("base_amount", 0.0),
                    }
                ]
                tax_totals["subtotals"] = subtotals

            first_subtotal = subtotals[0]
            first_subtotal.setdefault("tax_groups", [])
            first_subtotal.setdefault("tax_amount_currency", 0.0)
            first_subtotal.setdefault("tax_amount", 0.0)

            wht_total = 0.0
            for deduction in deduction_list:
                amount = deduction.get("amount", 0.0)
                if move.currency_id.is_zero(amount):
                    continue
                wht_tax = self.env["account.withholding.tax"].browse(
                    deduction["wht_tax_id"]
                )
                signed_wht_amount = -amount
                wht_total += signed_wht_amount
                first_subtotal["tax_groups"].append(
                    {
                        "id": -wht_tax.id,
                        "involved_tax_ids": [],
                        "tax_amount_currency": signed_wht_amount,
                        "tax_amount": signed_wht_amount,
                        "base_amount_currency": deduction.get("wht_amount_base", 0.0),
                        "base_amount": deduction.get("wht_amount_base", 0.0),
                        "display_base_amount_currency": None,
                        "display_base_amount": None,
                        "group_name": wht_tax.display_name,
                        "group_label": False,
                    }
                )

            if move.currency_id.is_zero(wht_total):
                continue

            first_subtotal["tax_amount_currency"] += wht_total
            first_subtotal["tax_amount"] += wht_total
            tax_totals["tax_amount_currency"] += wht_total
            tax_totals["tax_amount"] += wht_total
            tax_totals["total_amount_currency"] += wht_total
            tax_totals["total_amount"] += wht_total
            tax_totals["has_tax_groups"] = True
            move.tax_totals = tax_totals
