from contextlib import contextmanager

from odoo import api, models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _apply_sale_discount_gross_base_lines(self, base_lines_to_update):
        self.ensure_one()
        for base_line, to_update in base_lines_to_update:
            line = base_line["record"]
            if line.display_type != "product":
                continue
            if line.move_id != self:
                continue
            if not self.is_sale_document(include_receipts=True):
                continue
            discount_allocation_account = self._get_discount_allocation_account()
            if not discount_allocation_account or line.account_id == discount_allocation_account:
                continue
            if not line.discount:
                continue

            amount_currency = base_line["currency_id"].round(
                self.direction_sign
                * line.quantity
                * line.price_unit
                * line.discount
                / 100
            )
            if not amount_currency:
                continue
            rate = base_line.get("rate") or line.currency_rate
            if rate:
                balance = line.company_currency_id.round(amount_currency / rate)
            else:
                balance = 0.0

            to_update["amount_currency"] += amount_currency
            to_update["balance"] += balance

    @contextmanager
    def _sync_tax_lines(self, container):
        AccountTax = self.env["account.tax"]
        fake_base_line = AccountTax._prepare_base_line_for_taxes_computation(None)

        def get_base_lines(move):
            return move.line_ids.filtered(
                lambda line: line.display_type in ("product", "epd", "rounding", "cogs")
            )

        def get_tax_lines(move):
            return move.line_ids.filtered("tax_repartition_line_id")

        def get_value(record, field):
            return record._fields[field].convert_to_write(record[field], record)

        def get_tax_line_tracked_fields(line):
            return ("amount_currency", "balance", "analytic_distribution")

        def get_base_line_tracked_fields(line):
            grouping_key = AccountTax._prepare_base_line_grouping_key(fake_base_line)
            if line.move_id.is_invoice(include_receipts=True):
                extra_fields = ["price_unit", "quantity", "discount"]
            else:
                extra_fields = ["amount_currency"]
            return list(grouping_key.keys()) + extra_fields

        def field_has_changed(values, record, field):
            return get_value(record, field) != values.get(record, {}).get(field)

        def get_changed_lines(values, records, fields=None):
            return (
                record
                for record in records
                if record not in values
                or any(
                    field_has_changed(values, record, field)
                    for field in values[record]
                    if not fields or field in fields
                )
            )

        def any_field_has_changed(values, records, fields=None):
            return any(record for record in get_changed_lines(values, records, fields))

        def is_write_needed(line, values):
            return any(
                self.env["account.move.line"]
                ._fields[fname]
                .convert_to_write(line[fname], self)
                != values[fname]
                for fname in values
            )

        moves_values_before = {
            move: {
                field: get_value(move, field)
                for field in (
                    "currency_id",
                    "partner_id",
                    "move_type",
                    "invoice_currency_rate",
                    "invoice_date",
                )
            }
            for move in container["records"]
            if move.state == "draft"
        }
        base_lines_values_before = {
            move: {
                line: {
                    field: get_value(line, field) for field in get_base_line_tracked_fields(line)
                }
                for line in get_base_lines(move)
            }
            for move in container["records"]
        }
        tax_lines_values_before = {
            move: {
                line: {
                    field: get_value(line, field) for field in get_tax_line_tracked_fields(line)
                }
                for line in get_tax_lines(move)
            }
            for move in container["records"]
        }
        yield

        to_delete = []
        to_create = []
        for move in container["records"]:
            if move.state != "draft":
                continue

            tax_lines = get_tax_lines(move)
            base_lines = get_base_lines(move)
            move_tax_lines_values_before = tax_lines_values_before.get(move, {})
            move_base_lines_values_before = base_lines_values_before.get(move, {})
            if (
                move.is_invoice(include_receipts=True)
                and (
                    field_has_changed(moves_values_before, move, "currency_id")
                    or field_has_changed(moves_values_before, move, "move_type")
                )
            ):
                round_from_tax_lines = False
            elif any(
                line not in base_lines
                for line, values in move_base_lines_values_before.items()
                if values["tax_ids"]
            ):
                round_from_tax_lines = any_field_has_changed(
                    move_tax_lines_values_before, tax_lines
                )
            elif field_has_changed(
                moves_values_before, move, "invoice_currency_rate"
            ) and not field_has_changed(moves_values_before, move, "invoice_date"):
                round_from_tax_lines = "reapply_currency_rate"
            elif changed_lines := list(
                get_changed_lines(move_base_lines_values_before, base_lines)
            ):
                round_from_tax_lines = (
                    all(
                        not line.tax_ids
                        and not move_base_lines_values_before.get(line, {}).get("tax_ids")
                        for line in changed_lines
                    )
                    or (
                        list(move_tax_lines_values_before) != list(tax_lines)
                        or any(
                            self.env.is_protected(line._fields[fname], line)
                            for line in tax_lines
                            for fname in move_tax_lines_values_before[line]
                        )
                    )
                )

                if round_from_tax_lines and any(
                    line[field]
                    for line in changed_lines
                    for field in ("amount_currency", "balance")
                ):
                    continue
            else:
                continue

            base_lines_values, tax_lines_values = move._get_rounded_base_and_tax_lines(
                round_from_tax_lines=round_from_tax_lines
            )
            AccountTax._add_accounting_data_in_base_lines_tax_details(
                base_lines_values,
                move.company_id,
                include_caba_tags=move.always_tax_exigible,
            )
            tax_results = AccountTax._prepare_tax_lines(
                base_lines_values, move.company_id, tax_lines=tax_lines_values
            )
            move._apply_sale_discount_gross_base_lines(
                tax_results["base_lines_to_update"]
            )

            for base_line, to_update in tax_results["base_lines_to_update"]:
                line = base_line["record"]
                if is_write_needed(line, to_update):
                    line.write(to_update)

            for tax_line_vals in tax_results["tax_lines_to_delete"]:
                to_delete.append(tax_line_vals["record"].id)

            for tax_line_vals in tax_results["tax_lines_to_add"]:
                to_create.append(
                    {
                        **tax_line_vals,
                        "display_type": "tax",
                        "move_id": move.id,
                    }
                )

            for tax_line_vals, grouping_key, to_update in tax_results["tax_lines_to_update"]:
                line = tax_line_vals["record"]
                if is_write_needed(line, to_update):
                    line.write(to_update)

        if to_delete:
            self.env["account.move.line"].browse(to_delete).with_context(
                dynamic_unlink=True
            ).unlink()
        if to_create:
            self.env["account.move.line"].create(to_create)

    @api.depends(
        "line_ids.matched_debit_ids.debit_move_id.move_id.origin_payment_id.is_matched",
        "line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual",
        "line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency",
        "line_ids.matched_credit_ids.credit_move_id.move_id.origin_payment_id.is_matched",
        "line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual",
        "line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency",
        "line_ids.balance",
        "line_ids.currency_id",
        "line_ids.amount_currency",
        "line_ids.amount_residual",
        "line_ids.amount_residual_currency",
        "line_ids.payment_id.state",
        "line_ids.full_reconcile_id",
        "state",
    )
    def _compute_amount(self):
        res = super()._compute_amount()
        for move in self:
            if not move.is_invoice(True):
                continue
            discount_lines = move.line_ids.filtered(
                lambda line: line.display_type == "discount"
            )
            if not discount_lines:
                continue

            discount_balance = sum(discount_lines.mapped("balance"))
            discount_amount_currency = sum(discount_lines.mapped("amount_currency"))
            if (
                move.company_id.currency_id.is_zero(discount_balance)
                and move.currency_id.is_zero(discount_amount_currency)
            ):
                continue

            sign = move.direction_sign
            move.amount_untaxed += sign * discount_amount_currency
            move.amount_total += sign * discount_amount_currency
            move.amount_untaxed_signed -= discount_balance
            move.amount_untaxed_in_currency_signed -= discount_amount_currency
            if move.move_type == "entry":
                move.amount_total_signed = abs(move.amount_total)
                move.amount_total_in_currency_signed = abs(move.amount_total)
            else:
                move.amount_total_signed -= discount_balance
                move.amount_total_in_currency_signed = -(sign * move.amount_total)
        return res
