from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    out_cheque_line_id = fields.Many2one(
        "outbound.cheque.lines", string="Out Cheque Line", copy=False
    )
    in_cheque_line_id = fields.Many2one(
        "inbound.cheque.lines", string="In Cheque Line", copy=False
    )
    is_cheque_line = fields.Boolean(copy=False)


class AccountPayment(models.Model):
    _inherit = "account.payment"

    outbound_cheque_lines = fields.One2many(
        "outbound.cheque.lines", "payment_id", "Cheque"
    )
    inbound_cheque_lines = fields.One2many(
        "inbound.cheque.lines", "payment_id", "Cheque"
    )
    cheque_inbound_outbound_ids = fields.Many2many(
        "cheque.inbound.outbound", string="Cheque Paying/Receiving", copy=False
    )
    count_cheque_inbound_outbound = fields.Integer(
        compute="_count_cheque_inbound_outbound", string="Cheques"
    )
    outbound_cheque_lines_count = fields.Integer(compute="_count_outbound_cheque_lines")
    inbound_cheque_lines_count = fields.Integer(compute="_count_inbound_cheque_lines")

    is_advance_option = fields.Boolean()
    cheque_id = fields.Many2one("cheque.inbound.outbound", "Cheques")

    def _count_cheque_inbound_outbound(self):
        for payment in self:
            payment.count_cheque_inbound_outbound = len(
                payment.cheque_inbound_outbound_ids
            )

    def _count_outbound_cheque_lines(self):
        for payment in self:
            payment.outbound_cheque_lines_count = self.env[
                "outbound.cheque.lines"
            ].search_count([("payment_id", "=", payment.id)])

    def _count_inbound_cheque_lines(self):
        for payment in self:
            payment.inbound_cheque_lines_count = self.env[
                "inbound.cheque.lines"
            ].search_count([("payment_id", "=", payment.id)])

    def action_view_cheques(self):
        return self._get_action_view_cheques(self.cheque_inbound_outbound_ids)

    def _get_action_view_cheques(self, cheque):
        if self.payment_type == "inbound":
            action = self.env["ir.actions.actions"]._for_xml_id(
                "cheque_management.action_cheque_inbound_outbound_receiving"
            )
        else:
            action = self.env["ir.actions.actions"]._for_xml_id(
                "cheque_management.action_cheque_inbound_outbound_paying"
            )

        if len(cheque) > 1:
            action["domain"] = [("id", "in", cheque.ids)]
        elif cheque:
            form_view = [
                (
                    self.env.ref(
                        "cheque_management.cheque_inbound_outbound_form_view"
                    ).id,
                    "form",
                )
            ]
            if "views" in action:
                action["views"] = form_view + [
                    (state, view) for state, view in action["views"] if view != "form"
                ]
            else:
                action["views"] = form_view
            action["res_id"] = cheque.id
        action["context"] = {"create": 0}
        return action

    def _prepare_move_line_cheque_detail(self):
        line_vals_list = []
        # Cheque line
        if self.outbound_cheque_lines:
            for line in self.outbound_cheque_lines:
                if not self.payment_method_line_id.payment_account_id:
                    raise UserError(
                        _("Please set Outgoing Cheque Account first from Journal")
                    )

                total_amount_balance = self.currency_id._convert(
                    line.amount, self.company_id.currency_id, self.company_id, self.date
                )
                line_vals_name = (
                    str(line.cheque_id.name)
                    + "/"
                    + str(line.bank_account_id.bank_id.name)
                )
                if line.branch:
                    line_vals_name += "/" + str(line.branch)
                elif line.date:
                    line_vals_name += "/" + str(line.date)
                line_vals_list.append(
                    {
                        "name": line_vals_name,
                        "date_maturity": self.date,
                        "amount_currency": -line.amount,
                        "currency_id": self.currency_id.id,
                        "debit": total_amount_balance < 0.0
                        and -total_amount_balance
                        or 0.0,
                        "credit": total_amount_balance > 0.0
                        and total_amount_balance
                        or 0.0,
                        "partner_id": self.partner_id.id,
                        "account_id": self.payment_method_line_id.payment_account_id.id,
                        "out_cheque_line_id": line.id,
                        "is_cheque_line": True,
                    }
                )
        elif self.inbound_cheque_lines:
            for line in self.inbound_cheque_lines:
                if not self.payment_method_line_id.payment_account_id:
                    raise UserError(
                        _("Please set Incoming Cheque Account first from Journal")
                    )

                total_amount_balance = (
                    self.currency_id._convert(
                        line.amount,
                        self.company_id.currency_id,
                        self.company_id,
                        self.date,
                    )
                    * 1
                )
                line_vals_list.append(
                    {
                        "name": str(line.cheque_id)
                        + "/"
                        + str(line.bank_account_id.name)
                        + "/"
                        + str(line.branch)
                        + "/"
                        + str(line.date),
                        "date_maturity": self.date,
                        "amount_currency": line.amount,
                        "currency_id": self.currency_id.id,
                        "debit": total_amount_balance > 0.0
                        and total_amount_balance
                        or 0.0,
                        "credit": total_amount_balance < 0.0
                        and -total_amount_balance
                        or 0.0,
                        "partner_id": self.partner_id.id,
                        "account_id": self.payment_method_line_id.payment_account_id.id,
                        "in_cheque_line_id": line.id,
                        "is_cheque_line": True,
                    }
                )
        return line_vals_list

    def _get_liquidity_amount_currency_hook(self):
        liquidity_amount_currency = super(
            AccountPayment, self
        )._get_liquidity_amount_currency_hook()

        if not self.outbound_cheque_lines and not self.inbound_cheque_lines:
            return liquidity_amount_currency

        cheque_total = 0.0
        if self.outbound_cheque_lines:
            for line in self.outbound_cheque_lines:
                cheque_total += line.amount
        if self.inbound_cheque_lines:
            for line in self.inbound_cheque_lines:
                cheque_total += line.amount

        if self.payment_type == "inbound":
            # Receive money.
            liquidity_amount_currency = self.net_total_amount  # - cheque_total
        elif self.payment_type == "outbound":
            # Send money.
            liquidity_amount_currency = -self.net_total_amount  # + cheque_total
            # write_off_amount_currency *= -1
        else:
            liquidity_amount_currency = write_off_amount_currency = 0.0
        return liquidity_amount_currency

    def _get_counterpart_amount_currency_hook(
        self, liquidity_amount_currency, write_off_amount_currency
    ):
        counterpart_amount_currency = super(
            AccountPayment, self
        )._get_counterpart_amount_currency_hook(
            liquidity_amount_currency, write_off_amount_currency
        )

        if self.outbound_cheque_lines:
            cheque_total = 0.0
            for line in self.outbound_cheque_lines:
                cheque_total += line.amount

            cheque_liquidity_balance = self.currency_id._convert(
                -self.amount,
                self.company_id.currency_id,
                self.company_id,
                self.date,
            )
            counterpart_amount_currency = (
                -cheque_liquidity_balance - write_off_amount_currency
            )

        elif self.inbound_cheque_lines:
            cheque_total = 0.0
            for line in self.inbound_cheque_lines:
                cheque_total += line.amount
            cheque_liquidity_balance = self.currency_id._convert(
                self.amount,
                self.company_id.currency_id,
                self.company_id,
                self.date,
            )
            counterpart_amount_currency = (
                -cheque_liquidity_balance - write_off_amount_currency
            )

        return counterpart_amount_currency

    def _get_counterpart_balance_hook(self, liquidity_balance, write_off_balance):
        counterpart_balance = super(AccountPayment, self)._get_counterpart_balance_hook(
            liquidity_balance, write_off_balance
        )
        if self.outbound_cheque_lines:
            cheque_total = 0.0
            for line in self.outbound_cheque_lines:
                cheque_total += line.amount

            cheque_liquidity_balance = self.currency_id._convert(
                -self.amount,
                self.company_id.currency_id,
                self.company_id,
                self.date,
            )
            counterpart_balance = -cheque_liquidity_balance - write_off_balance
        elif self.inbound_cheque_lines:
            cheque_total = 0.0
            for line in self.inbound_cheque_lines:
                cheque_total += line.amount
            cheque_liquidity_balance = self.currency_id._convert(
                self.amount,
                self.company_id.currency_id,
                self.company_id,
                self.date,
            )
            counterpart_balance = -cheque_liquidity_balance - write_off_balance

        return counterpart_balance

    def _get_liquidity_line_vals_hook(self, liquidity_line_vals):
        line_vals_list = super(AccountPayment, self)._get_liquidity_line_vals_hook(
            liquidity_line_vals
        )
        if self.outbound_cheque_lines or self.inbound_cheque_lines:
            cheque_lines = self._prepare_move_line_cheque_detail()
            cheque_total = 0.0
            for line in self.inbound_cheque_lines or self.outbound_cheque_lines:
                cheque_total += line.amount

            if cheque_total == self.amount:
                line_vals_list = cheque_lines
            else:
                if line_vals_list:
                    liq_line = line_vals_list[0]
                    if self.payment_type == "inbound":
                        liq_line.update(
                            {
                                "amount_currency": (
                                    self.net_total_amount - cheque_total
                                ),
                                "debit": self.net_total_amount - cheque_total,
                                "credit": 0,  # total_amount_balance > 0.0 and total_amount_balance or 0.0,
                            }
                        )
                    else:
                        liq_line.update(
                            {
                                "amount_currency": (
                                    self.net_total_amount - cheque_total
                                ),
                                "debit": 0,  # total_amount_balance < 0.0 and -total_amount_balance or 0.0,
                                "credit": self.net_total_amount - cheque_total,
                            }
                        )
                line_vals_list.extend(cheque_lines)
        return line_vals_list

    def _get_receivable_payable_line_vals_hook(self, receivable_payable_line_vals):
        line_vals_list = super(
            AccountPayment, self
        )._get_receivable_payable_line_vals_hook(receivable_payable_line_vals)
        ctx = self._context
        if (
            self.outbound_cheque_lines
            and line_vals_list
            and self.payment_type == "outbound"
            and not self.is_multi_writeoff
            and ctx.get("payment_difference") != "reconcile"
        ):
            liq_line = line_vals_list[0]
            liq_line.update(
                {
                    "amount_currency": self.net_total_amount,
                    "debit": self.net_total_amount,
                    "credit": 0,
                }
            )
        return line_vals_list

    def _execute_main_logic_hook(self):
        for pay in self.with_context(skip_account_move_synchronization=True):
            liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()

            to_remove_lines = []
            for line in self.move_id.line_ids:
                if line.is_cheque_line:
                    if not line.out_cheque_line_id and not line.in_cheque_line_id:
                        to_remove_lines.append((3, line.id))

            # Make sure to preserve the write-off amount.
            # This allows to create a new payment with custom 'line_ids'.

            if liquidity_lines and counterpart_lines and writeoff_lines:
                counterpart_amount = sum(counterpart_lines.mapped("amount_currency"))
                writeoff_amount = sum(writeoff_lines.mapped("amount_currency"))

                # To be consistent with the payment_difference made in account.payment.register,
                # 'writeoff_amount' needs to be signed regarding the 'amount' field before the write.
                # Since the write is already done at this point, we need to base the computation on accounting values.
                if (counterpart_amount > 0.0) == (writeoff_amount > 0.0):
                    sign = -1
                else:
                    sign = 1
                writeoff_amount = abs(writeoff_amount) * sign

                write_off_line_vals = {
                    "name": writeoff_lines[0].name,
                    "amount": writeoff_amount,
                    "account_id": writeoff_lines[0].account_id.id,
                }
            else:
                write_off_line_vals = {}

            line_vals_list = pay._prepare_move_line_default_vals(
                write_off_line_vals=write_off_line_vals
            )

            line_ids_commands = []
            if liquidity_lines:
                line_ids_commands.append((1, liquidity_lines.id, line_vals_list[0]))
            else:
                line_ids_commands.append((0, 0, line_vals_list[0]))

            if counterpart_lines:
                line_ids_commands.append((1, counterpart_lines.id, line_vals_list[1]))
            else:
                line_ids_commands.append((0, 0, line_vals_list[1]))

            for line in writeoff_lines:
                line_ids_commands.append((2, line.id))

            for extra_line_vals in line_vals_list[2:]:
                line_ids_commands.append((0, 0, extra_line_vals))

            if to_remove_lines:
                line_ids_commands.extend(to_remove_lines)

            # Update the existing journal items.
            # If dealing with multiple write-off lines, they are dropped and a new one is generated.
            pay.move_id.write(
                {
                    "partner_id": pay.partner_id.id,
                    "currency_id": pay.currency_id.id,
                    "partner_bank_id": pay.partner_bank_id.id,
                    "line_ids": line_ids_commands,
                }
            )

    def _get_field_name_list_hook(self):
        field_name_list = super(AccountPayment, self)._get_field_name_list_hook()
        field_name_list.extend(["inbound_cheque_lines", "outbound_cheque_lines"])
        return field_name_list

    @api.model_create_multi
    def create(self, vals):
        res = super(AccountPayment, self).create(vals)
        cheque_inbound_outbound_list = []
        if res.outbound_cheque_lines:
            if not res.journal_id.payment_account_id:
                raise UserError(
                    _("Please set Outgoing Cheque Account first from Journal")
                )

            for line in res.outbound_cheque_lines:
                if not line.is_cheque_created:
                    payment_method_line_id = self.env[
                        "account.payment.method.line"
                    ].search(
                        [
                            ("payment_type", "=", "inbound"),
                            ("journal_id", "=", res.journal_id.id),
                        ],
                        order="id asc",
                        limit=1,
                    )
                    existing_cheque_inbound_outbound_id = self.env[
                        "cheque.inbound.outbound"
                    ].search([("name", "=", line.cheque_id.name)])
                    if existing_cheque_inbound_outbound_id:
                        payment_list = []
                        for payment in res:
                            payment_list.append(payment.id)

                        if existing_cheque_inbound_outbound_id.payment_ids:
                            for (
                                existing_payment
                            ) in existing_cheque_inbound_outbound_id.payment_ids:
                                payment_list.append(existing_payment.id)

                        existing_cheque_inbound_outbound_id.write(
                            {"payment_ids": [(6, 1, payment_list)]}
                        )
                        if existing_cheque_inbound_outbound_id.state != "paid":
                            new_total = sum(
                                existing_cheque_inbound_outbound_id.payment_ids.mapped(
                                    "amount"
                                )
                            )
                            existing_cheque_inbound_outbound_id.write(
                                {
                                    "amount": new_total,
                                    "cheque_amount": new_total,
                                }
                            )
                        cheque_inbound_outbound_list.append(
                            existing_cheque_inbound_outbound_id.id
                        )
                    else:
                        payment_list = []
                        for payment in res:
                            payment_list.append(payment.id)
                        new_cheque_paying = self.env["cheque.inbound.outbound"].create(
                            {
                                "name": line.cheque_id.name,
                                "cheque_id": line.cheque_id.id,
                                "cheque_book_id": line.cheque_id.cheque_book_id.id,
                                "bank_account_journal_id": res.journal_id.id,
                                "pay_partner_id": line.payment_id.partner_id.id,
                                "partner_name": line.payment_id.partner_id.name,
                                "ac_payee": line.ac_payee,
                                "memo": line.remarks,
                                "amount": line.amount,
                                "cheque_date": line.date,
                                "date": res.date,
                                "payment_ids": [(6, 0, payment_list)],
                                "cheque_amount": line.amount,
                                "cheque_type": "inbound",
                                "payment_method_line_id": payment_method_line_id.id,
                                "payment_method_line_account_id": res.payment_method_line_id.payment_account_id.id,
                            }
                        )
                        cheque_inbound_outbound_list.append(new_cheque_paying.id)
                        self.env["cheque.payment.detail.lines"].create(
                            {
                                "payment_ref": res.id,
                                "date": res.date,
                                "currency_id": res.currency_id.id,
                                "amount": res.amount,
                                "cheque_inbound_outbound_id": new_cheque_paying.id,
                            }
                        )
                        new_cheque_paying.action_waiting_confirm()
                        line.cheque_id.status = "waiting_confirm"
                        line.cheque_id.date = line.date
                        line.cheque_id.pay_to = line.payment_id.partner_id.id
                        line.cheque_id.amount = line.amount
                        line.cheque_id.memo = line.remarks
                    line.is_cheque_created = True

        if res.inbound_cheque_lines:
            for line in res.inbound_cheque_lines:
                if not line.is_cheque_created:
                    payment_method_line_id = self.env[
                        "account.payment.method.line"
                    ].search(
                        [
                            ("payment_type", "=", "outbound"),
                            ("journal_id", "=", res.journal_id.id),
                        ],
                        order="id asc",
                        limit=1,
                    )
                    existing_cheque_inbound_outbound_id = self.env[
                        "cheque.inbound.outbound"
                    ].search([("name", "=", line.cheque_id)])
                    if existing_cheque_inbound_outbound_id:
                        payment_list = []
                        for payment in res:
                            payment_list.append(payment.id)

                        if existing_cheque_inbound_outbound_id.payment_ids:
                            for (
                                existing_payment
                            ) in existing_cheque_inbound_outbound_id.payment_ids:
                                payment_list.append(existing_payment.id)

                        existing_cheque_inbound_outbound_id.write(
                            {"payment_ids": [(6, 0, payment_list)]}
                        )
                        if existing_cheque_inbound_outbound_id.state != "paid":
                            new_total = sum(
                                existing_cheque_inbound_outbound_id.payment_ids.mapped(
                                    "amount"
                                )
                            )
                            existing_cheque_inbound_outbound_id.write(
                                {
                                    "amount": new_total,
                                    "cheque_amount": new_total,
                                }
                            )
                        cheque_inbound_outbound_list.append(
                            existing_cheque_inbound_outbound_id.id
                        )
                    else:
                        payment_list = []
                        for payment in res:
                            payment_list.append(payment.id)
                        new_cheque_receiving = self.env[
                            "cheque.inbound.outbound"
                        ].create(
                            {
                                "name": line.cheque_id,
                                "pay_partner_id": line.payment_id.partner_id.id,
                                "partner_name": line.payment_id.partner_id.name,
                                "amount": line.amount,
                                "date": res.date,
                                "cheque_date": line.date,
                                "bank_account_journal_id": res.journal_id.id,
                                "cheque_bank_id": line.bank_account_id.id,
                                "cheque_bank_branch": line.branch,
                                "memo": line.remarks,
                                "ac_payee": line.ac_payee,
                                "payment_ids": [(6, 0, payment_list)],
                                "cheque_amount": line.amount,
                                "cheque_type": "outbound",
                                "payment_method_line_id": payment_method_line_id.id,
                                "payment_method_line_account_id": res.payment_method_line_id.payment_account_id.id,
                            }
                        )
                        cheque_inbound_outbound_list.append(new_cheque_receiving.id)
                        new_cheque_receiving.action_waiting_confirm()
                    line.is_cheque_created = True
        res.cheque_inbound_outbound_ids = [(6, 0, cheque_inbound_outbound_list)]
        return res

    def write(self, vals):
        for rec in self:
            if vals.get("inbound_cheque_lines"):
                for line in rec.inbound_cheque_lines:
                    cheque_paying_obj = self.env["cheque.inbound.outbound"].search(
                        [
                            ("state", "=", "waiting_confirm"),
                            ("bank_account_journal_id", "=", rec.journal_id.id),
                            ("name", "=", line.cheque_id),
                            ("payment_id", "=", rec.id),
                        ]
                    )
                    if cheque_paying_obj:
                        cheque_paying_obj.state = "draft"
                        cheque_paying_obj.unlink()
        res = super(AccountPayment, self).write(vals)
        cheque_inbound_outbound_list = []
        if vals.get("outbound_cheque_lines"):
            if self.outbound_cheque_lines:
                if not self.payment_method_line_id.payment_account_id:
                    raise UserError(
                        _("Please set Outgoing Cheque Account first from Journal")
                    )

                for line in self.outbound_cheque_lines:
                    if not line.is_cheque_created:
                        payment_method_line_id = self.env[
                            "account.payment.method.line"
                        ].search(
                            [
                                ("payment_type", "=", "inbound"),
                                ("journal_id", "=", self.journal_id.id),
                            ],
                            order="id asc",
                            limit=1,
                        )
                        existing_cheque_inbound_outbound_id = self.env[
                            "cheque.inbound.outbound"
                        ].search([("name", "=", line.cheque_id.name)])
                        if existing_cheque_inbound_outbound_id:
                            payment_list = []
                            for payment in self:
                                payment_list.append(payment.id)

                            if existing_cheque_inbound_outbound_id.payment_ids:
                                for (
                                    existing_payment
                                ) in existing_cheque_inbound_outbound_id.payment_ids:
                                    payment_list.append(existing_payment.id)

                            existing_cheque_inbound_outbound_id.write(
                                {"payment_ids": [(6, 1, payment_list)]}
                            )
                            if existing_cheque_inbound_outbound_id.state != "paid":
                                new_total = sum(
                                    existing_cheque_inbound_outbound_id.payment_ids.mapped(
                                        "amount"
                                    )
                                )
                                existing_cheque_inbound_outbound_id.write(
                                    {
                                        "amount": new_total,
                                        "cheque_amount": new_total,
                                    }
                                )
                            cheque_inbound_outbound_list.append(
                                existing_cheque_inbound_outbound_id.id
                            )
                        else:
                            payment_list = []
                            for payment in self:
                                payment_list.append(payment.id)
                            new_cheque_paying = self.env[
                                "cheque.inbound.outbound"
                            ].create(
                                {
                                    "name": line.cheque_id.name,
                                    "cheque_id": line.cheque_id.id,
                                    "cheque_book_id": line.cheque_id.cheque_book_id.id,
                                    "bank_account_journal_id": self.journal_id.id,
                                    "pay_partner_id": line.payment_id.partner_id.id,
                                    "partner_name": line.payment_id.partner_id.name,
                                    "ac_payee": line.ac_payee,
                                    "memo": line.remarks,
                                    "amount": line.amount,
                                    "cheque_date": line.date,
                                    "date": self.date,
                                    "payment_ids": [(6, 0, payment_list)],
                                    "cheque_amount": line.amount,
                                    "cheque_type": "inbound",
                                    "payment_method_line_id": payment_method_line_id.id,
                                    "payment_method_line_account_id": self.payment_method_line_id.payment_account_id.id,
                                }
                            )
                            cheque_inbound_outbound_list.append(new_cheque_paying.id)
                            self.env["cheque.payment.detail.lines"].create(
                                {
                                    "payment_ref": self.id,
                                    "date": self.date,
                                    "currency_id": self.currency_id.id,
                                    "amount": self.amount,
                                    "cheque_inbound_outbound_id": new_cheque_paying.id,
                                }
                            )
                            new_cheque_paying.action_waiting_confirm()
                            line.cheque_id.status = "waiting_confirm"
                            line.cheque_id.date = line.date
                            line.cheque_id.pay_to = line.payment_id.partner_id.id
                            line.cheque_id.amount = line.amount
                            line.cheque_id.memo = line.remarks
                        line.is_cheque_created = True

                self.cheque_inbound_outbound_ids = [
                    (6, 0, cheque_inbound_outbound_list)
                ]

        if vals.get("inbound_cheque_lines"):
            if self.inbound_cheque_lines:
                for line in self.inbound_cheque_lines:
                    if not line.is_cheque_created:
                        payment_method_line_id = self.env[
                            "account.payment.method.line"
                        ].search(
                            [
                                ("payment_type", "=", "outbound"),
                                ("journal_id", "=", self.journal_id.id),
                            ],
                            order="id asc",
                            limit=1,
                        )
                        existing_cheque_inbound_outbound_id = self.env[
                            "cheque.inbound.outbound"
                        ].search([("name", "=", line.cheque_id)])
                        if existing_cheque_inbound_outbound_id:
                            payment_list = []
                            for payment in self:
                                payment_list.append(payment.id)

                            if existing_cheque_inbound_outbound_id.payment_ids:
                                for (
                                    existing_payment
                                ) in existing_cheque_inbound_outbound_id.payment_ids:
                                    payment_list.append(existing_payment.id)

                            existing_cheque_inbound_outbound_id.write(
                                {"payment_ids": [(6, 0, payment_list)]}
                            )
                            if existing_cheque_inbound_outbound_id.state != "paid":
                                new_total = sum(
                                    existing_cheque_inbound_outbound_id.payment_ids.mapped(
                                        "amount"
                                    )
                                )
                                existing_cheque_inbound_outbound_id.write(
                                    {
                                        "amount": new_total,
                                        "cheque_amount": new_total,
                                    }
                                )
                            cheque_inbound_outbound_list.append(
                                existing_cheque_inbound_outbound_id.id
                            )
                        else:
                            payment_list = []
                            for payment in self:
                                payment_list.append(payment.id)
                            new_cheque_receiving = self.env[
                                "cheque.inbound.outbound"
                            ].create(
                                {
                                    "name": line.cheque_id,
                                    "pay_partner_id": line.payment_id.partner_id.id,
                                    "partner_name": line.payment_id.partner_id.name,
                                    "amount": line.amount,
                                    "date": self.date,
                                    "cheque_date": line.date,
                                    "bank_account_journal_id": self.journal_id.id,
                                    "cheque_bank_id": line.bank_account_id.id,
                                    "cheque_bank_branch": line.branch,
                                    "memo": line.remarks,
                                    "ac_payee": line.ac_payee,
                                    "payment_ids": [(6, 0, payment_list)],
                                    "cheque_amount": line.amount,
                                    "cheque_type": "outbound",
                                    "payment_method_line_id": payment_method_line_id.id,
                                    "payment_method_line_account_id": self.payment_method_line_id.payment_account_id.id,
                                }
                            )
                            cheque_inbound_outbound_list.append(new_cheque_receiving.id)
                            new_cheque_receiving.action_waiting_confirm()
                        line.is_cheque_created = True

                self.cheque_inbound_outbound_ids = [
                    (6, 0, cheque_inbound_outbound_list)
                ]

        return res

    @api.depends("invoice_ids.payment_state", "move_id.line_ids.amount_residual")
    def _compute_state(self):
        for payment in self:
            if not payment.state:
                payment.state = "draft"
            # in_process --> paid
            if (move := payment.move_id) and payment.state in ("paid", "in_process"):
                liquidity, _counterpart, _writeoff = payment._seek_for_lines()
                if liquidity:
                    liquidity = liquidity[0]
                payment.state = (
                    "paid"
                    if move.company_currency_id.is_zero(
                        sum(liquidity.mapped("amount_residual"))
                    )
                    or (liquidity and not liquidity.account_id.reconcile)
                    else "in_process"
                )
            if (
                payment.state == "in_process"
                and payment.invoice_ids
                and all(
                    invoice.payment_state == "paid" for invoice in payment.invoice_ids
                )
            ):
                payment.state = "paid"


class OutboundChequeLine(models.Model):
    _name = "outbound.cheque.lines"
    _description = "Outbound Cheque Lines"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "cheque_id"

    payment_id = fields.Many2one("account.payment", "Payment")
    payment_type = fields.Selection(
        [
            ("outbound", "Send Money"),
            ("inbound", "Receive Money"),
        ],
        string="Payment Type",
        related="payment_id.payment_type",
        store=True,
    )
    journal_id = fields.Many2one(
        related="payment_id.journal_id", store=True, index=True, copy=False
    )
    cheque_id = fields.Many2one(
        "cheque.book.lines", "Cheque", domain=[("status", "=", "draft")]
    )
    bank_account_id = fields.Many2one(
        "res.partner.bank", "Bank", related="journal_id.bank_account_id", store=True
    )
    branch = fields.Char("Branch")
    date = fields.Date("Date", default=fields.Date.context_today)
    ac_payee = fields.Boolean("A/C Payee", default=True)
    amount = fields.Float("Amount")
    remarks = fields.Text("Remarks")
    is_cheque_created = fields.Boolean("Is Cheque Created?")

    @api.model_create_multi
    def create(self, vals_list):
        res = super(OutboundChequeLine, self).create(vals_list)
        for vals in vals_list:
            if vals.get("amount") <= 0.0:
                raise UserError(
                    _(
                        "Amount must be greater than 0 in cheque line %s .",
                        res.cheque_id.name,
                    )
                )
        return res

    def write(self, vals):
        res = super(OutboundChequeLine, self).write(vals)
        for rec in self:
            if rec.amount <= 0.0:
                raise UserError(
                    _(
                        "Amount must be greater than 0 in cheque line %s .",
                        rec.cheque_id.name,
                    )
                )
        return res


class InboundChequeLine(models.Model):
    _name = "inbound.cheque.lines"
    _description = "Inbound Cheque Lines"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "cheque_id"

    payment_id = fields.Many2one("account.payment", "Payment")
    payment_type = fields.Selection(
        [
            ("outbound", "Send Money"),
            ("inbound", "Receive Money"),
        ],
        string="Payment Type",
        related="payment_id.payment_type",
        store=True,
    )
    cheque_id = fields.Char("Cheque")
    bank_account_id = fields.Many2one("res.bank", "Bank")
    branch = fields.Char("Branch")
    date = fields.Date("Date", default=fields.Date.context_today)
    ac_payee = fields.Boolean("A/C Payee", default=True)
    amount = fields.Float("Amount")
    remarks = fields.Text("Remarks")
    is_cheque_created = fields.Boolean("Is Cheque Created?")

    @api.model_create_multi
    def create(self, vals_list):
        res = super(InboundChequeLine, self).create(vals_list)
        for vals in vals_list:
            if vals.get("amount"):
                if vals.get("amount") <= 0.0:
                    raise UserError(
                        _(
                            "Amount must be greater than 0 in cheque line %s .",
                            res.cheque_id,
                        )
                    )
        return res

    def write(self, vals):
        res = super(InboundChequeLine, self).write(vals)
        for rec in self:
            if vals.get("amount"):
                if vals.get("amount") <= 0.0:
                    raise UserError(
                        _(
                            "Amount must be greater than 0 in cheque line %s .",
                            rec.cheque_id,
                        )
                    )
        return res
