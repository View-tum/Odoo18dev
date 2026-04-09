from collections import defaultdict

from odoo import _, api, fields, models
from odoo.osv import expression
from odoo.tools import frozendict


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    discount_allocation_hide = fields.Boolean(
        compute="_compute_discount_allocation_hide",
        store=True,
    )
    gross_debit = fields.Monetary(
        currency_field="company_currency_id",
        compute="_compute_gross_debit_credit",
        store=True,
        readonly=True,
    )
    gross_credit = fields.Monetary(
        currency_field="company_currency_id",
        compute="_compute_gross_debit_credit",
        store=True,
        readonly=True,
    )

    @api.depends(
        "display_type",
        "account_id",
        "move_id.move_type",
        "move_id.line_ids.account_id",
        "move_id.line_ids.display_type",
        "move_id.company_id.account_discount_expense_allocation_id",
        "move_id.company_id.account_discount_income_allocation_id",
    )
    def _compute_discount_allocation_hide(self):
        for line in self:
            if line.display_type != "discount":
                line.discount_allocation_hide = False
                continue
            product_accounts = line.move_id.line_ids.filtered(
                lambda l: l.display_type == "product"
            ).account_id
            line.discount_allocation_hide = bool(
                line.account_id and line.account_id in product_accounts
            )

    @api.depends(
        "display_type",
        "balance",
        "discount",
        "price_unit",
        "quantity",
        "currency_rate",
        "currency_id",
        "company_currency_id",
        "move_id.move_type",
        "move_id.company_id.account_discount_expense_allocation_id",
        "move_id.company_id.account_discount_income_allocation_id",
    )
    def _compute_gross_debit_credit(self):
        discount_accounts_by_move = {
            move.id: set(
                move.line_ids.filtered(lambda l: l.display_type == "discount")
                .mapped("account_id")
                .ids
            )
            for move in self.mapped("move_id")
        }
        for line in self:
            gross_balance = line.balance
            if (
                line.display_type == "product"
                and line.move_id.is_invoice(include_receipts=True)
                and line.discount
                and line.move_id._get_discount_allocation_account()
            ):
                has_product_discount_line = (
                    line.account_id.id
                    in discount_accounts_by_move.get(line.move_id.id, set())
                )
                if has_product_discount_line:
                    discount_amount_currency = line.currency_id.round(
                        line.move_id.direction_sign
                        * line.quantity
                        * line.price_unit
                        * line.discount
                        / 100
                    )
                    if line.currency_rate:
                        discount_balance = line.company_currency_id.round(
                            discount_amount_currency / line.currency_rate
                        )
                    else:
                        discount_balance = 0.0
                    gross_balance = line.balance + discount_balance
            line.gross_debit = gross_balance if gross_balance > 0 else 0.0
            line.gross_credit = -gross_balance if gross_balance < 0 else 0.0

    @api.depends(
        "account_id",
        "company_id",
        "discount",
        "price_unit",
        "quantity",
        "currency_rate",
        "analytic_distribution",
    )
    def _compute_discount_allocation_needed(self):
        line2discounted_amount = {}
        for line in self.move_id.line_ids:
            if line.display_type != "product":
                continue
            discount_allocation_account = line.move_id._get_discount_allocation_account()
            if not discount_allocation_account or line.account_id == discount_allocation_account:
                continue
            amount = line.currency_id.round(
                line.move_id.direction_sign
                * line.quantity
                * line.price_unit
                * line.discount
                / 100
            )
            if not amount:
                continue

            if line.move_id.is_sale_document(include_receipts=True):
                discounted_amounts = [(discount_allocation_account, -amount)]
            else:
                discounted_amounts = [
                    (line.account_id, amount),
                    (discount_allocation_account, -amount),
                ]
            line2discounted_amount[line] = discounted_amounts

        distribution_totals = defaultdict(lambda: defaultdict(float))
        for line, discounted_amounts in line2discounted_amount.items():
            for account, amount in discounted_amounts:
                for analytic_account_id in line.analytic_distribution or {}:
                    distribution_totals[
                        frozendict(
                            {
                                "move_id": line.move_id.id,
                                "account_id": account.id,
                                "currency_rate": line.currency_rate,
                            }
                        )
                    ][analytic_account_id] += amount

        for line in self:
            line.discount_allocation_dirty = True
            if line not in line2discounted_amount:
                line.discount_allocation_needed = False
                continue

            discount_allocation_needed = {}
            for account, amount in line2discounted_amount[line]:
                key = frozendict(
                    {
                        "move_id": line.move_id.id,
                        "account_id": account.id,
                        "currency_rate": line.currency_rate,
                    }
                )
                dist = distribution_totals[key]
                total = sum(dist.values()) or 1
                discount_allocation_needed[key] = frozendict(
                    {
                        "display_type": "discount",
                        "name": _("Discount"),
                        "amount_currency": amount,
                        "analytic_distribution": {
                            account_id: 100 * value / total
                            for account_id, value in dist.items()
                        },
                    }
                )
            line.discount_allocation_needed = discount_allocation_needed

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        if self.env.context.get("hide_discount_allocation_lines"):
            domain = expression.AND([domain, [("discount_allocation_hide", "=", False)]])
        return super()._search(
            domain,
            offset=offset,
            limit=limit,
            order=order,
        )
