# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    # Cheque Lines
    wizard_outbound_cheque_lines = fields.One2many(
        "wizard.outbound.cheque.lines", "wizard_id", string="Cheque"
    )
    wizard_inbound_cheque_lines = fields.One2many(
        "wizard.inbound.cheque.lines", "wizard_id", string="Cheque"
    )
    is_cheque_incoming = fields.Boolean(
        "Cheque Incoming", related="payment_method_line_id.is_cheque_incoming_line"
    )
    is_cheque_outgoing = fields.Boolean(
        "Cheque Outgoing", related="payment_method_line_id.is_cheque_outgoing_line"
    )
    is_cheque_already_added_ids = fields.Many2many(
        "cheque.book.lines",
        string="Cheques",
        compute="_compute_cheque_already_added",
        store=True,
    )

    @api.depends(
        "payment_method_line_id",
        "wizard_outbound_cheque_lines",
        "wizard_outbound_cheque_lines.cheque_id",
    )
    def _compute_cheque_already_added(self):
        for rec in self:
            cheque_line = self.env["cheque.book.lines"].search(
                [
                    ("cheque_book_id.state", "=", "done"),
                    ("status", "=", "draft"),
                    ("bank_account_journal_id", "=", rec.journal_id.id),
                ]
            )
            rec.is_cheque_already_added_ids = [(6, 0, cheque_line.ids)]
            # if rec.wizard_outbound_cheque_lines:
            #     for wizard_outbound_cheque in rec.wizard_outbound_cheque_lines:
            #         rec.is_cheque_already_added_ids = [(2, wizard_outbound_cheque.cheque_id.id)]

    def check_customers(self):
        customer_ids = self.line_ids.move_id.mapped("partner_id.id")

        if self.line_ids[0].move_id.move_type == "in_invoice":
            if (
                len(set(customer_ids)) > 1
                and self.payment_method_line_id.is_cheque_outgoing_line
            ):
                raise UserError(
                    _("You can not create Cheque payment for multiple customer.")
                )

        if self.line_ids[0].move_id.move_type == "out_invoice":
            if (
                len(set(customer_ids)) > 1
                and self.payment_method_line_id.code in ['cheque_incoming', 'cheque_outgoing']
            ):
                raise UserError(
                    _("You can not create Cheque payment for multiple customer.")
                )

    def action_create_payments(self):
        if self.is_cheque_incoming and not self.wizard_inbound_cheque_lines:
            raise UserError(
                _("Please Add Inbound Cheque line to create payment with Cheque.")
            )

        if self.is_cheque_outgoing and not self.wizard_outbound_cheque_lines:
            raise UserError(
                _("Please Add Outbound Cheque line to create payment with Cheque.")
            )

        self.check_customers()

        total_cheque_amount = 0.0
        if self.wizard_outbound_cheque_lines:
            total_cheque_amount += sum(
                outbound.amount for outbound in self.wizard_outbound_cheque_lines
            )
        if self.wizard_inbound_cheque_lines:
            total_cheque_amount += sum(
                inbound.amount for inbound in self.wizard_inbound_cheque_lines
            )
        if total_cheque_amount and self.amount < total_cheque_amount:
            raise UserError(_("Cheque amount can not more than actual amount."))

        res = super(AccountPaymentRegister, self).action_create_payments()

        if self.wizard_outbound_cheque_lines or self.wizard_inbound_cheque_lines:
            payment_ids = self._get_created_payment_records(res)
            if not payment_ids:
                payment_ids = self._fallback_find_created_payments()

            if payment_ids:
                if self.wizard_outbound_cheque_lines:
                    wizard_outbound_cheque_lines_list = [
                        (
                            0,
                            0,
                            {
                                "payment_type": outbound_cheque.payment_type,
                                "journal_id": outbound_cheque.journal_id.id,
                                "cheque_id": outbound_cheque.cheque_id.id,
                                "bank_account_id": outbound_cheque.bank_account_id.id,
                                "branch": outbound_cheque.branch,
                                "date": outbound_cheque.date,
                                "ac_payee": outbound_cheque.ac_payee,
                                "amount": outbound_cheque.amount,
                                "remarks": outbound_cheque.remarks,
                            },
                        )
                        for outbound_cheque in self.wizard_outbound_cheque_lines
                    ]
                    payment_ids.update(
                        {"outbound_cheque_lines": wizard_outbound_cheque_lines_list}
                    )
                    self._append_cheque_names_to_move_lines(
                        payment_ids,
                        [
                            outbound_cheque_name.cheque_id.name
                            for outbound_cheque_name in self.wizard_outbound_cheque_lines
                        ],
                    )

                if self.wizard_inbound_cheque_lines:
                    wizard_inbound_cheque_lines_list = [
                        (
                            0,
                            0,
                            {
                                "payment_type": inbound_cheque.payment_type,
                                "cheque_id": inbound_cheque.cheque_id,
                                "bank_account_id": inbound_cheque.bank_account_id.id,
                                "branch": inbound_cheque.branch,
                                "date": inbound_cheque.date,
                                "ac_payee": inbound_cheque.ac_payee,
                                "amount": inbound_cheque.amount,
                                "remarks": inbound_cheque.remarks,
                            },
                        )
                        for inbound_cheque in self.wizard_inbound_cheque_lines
                    ]
                    payment_ids.update(
                        {"inbound_cheque_lines": wizard_inbound_cheque_lines_list}
                    )
                    self._append_cheque_names_to_move_lines(
                        payment_ids,
                        [
                            inbound_cheque_line.cheque_id
                            for inbound_cheque_line in self.wizard_inbound_cheque_lines
                        ],
                    )

        return res

    def _get_created_payment_records(self, action_result):
        payment_obj = self.env["account.payment"]
        if not isinstance(action_result, dict):
            return payment_obj

        if action_result.get("res_model") != "account.payment":
            return payment_obj

        if action_result.get("res_id"):
            return payment_obj.browse(action_result["res_id"]).exists()

        domain = action_result.get("domain")
        if domain:
            return payment_obj.search(domain)
        return payment_obj

    def _fallback_find_created_payments(self):
        payment_obj = self.env["account.payment"]

        if self.communication:
            payment_id = payment_obj.search(
                [("memo", "=", self.communication)],
                order="id desc",
                limit=1,
            )
            if payment_id:
                return payment_id

        payment_ids = payment_obj
        for line in self.line_ids:
            payment_ids |= payment_obj.search([("memo", "=", line.name)])
        return payment_ids

    def _append_cheque_names_to_move_lines(self, payments, cheque_names):
        suffix = "".join(f" : Cheque : {name}" for name in cheque_names if name)
        if not suffix:
            return
        for move_line in payments.mapped("move_id.line_ids"):
            move_line.name = f"{move_line.name or ''}{suffix}"


class WizardOutboundChequeLine(models.TransientModel):
    _name = "wizard.outbound.cheque.lines"
    _description = "Outbound Cheque Lines"

    wizard_id = fields.Many2one("account.payment.register", "Wizard")
    payment_type = fields.Selection(
        [
            ("outbound", "Send Money"),
            ("inbound", "Receive Money"),
        ],
        string="Payment Type",
        related="wizard_id.payment_type",
        store=True,
    )
    journal_id = fields.Many2one(
        related="wizard_id.journal_id", store=True, index=True, copy=False
    )
    cheque_id = fields.Many2one(
        "cheque.book.lines",
        "Cheque",
        domain="[('cheque_book_id.state', '=', 'done'), ('status', '=', 'draft'), ('bank_account_journal_id', '=', journal_id), ('id', 'in', is_cheque_already_added_ids)]",
    )
    bank_account_id = fields.Many2one(
        "res.partner.bank", "Bank", related="journal_id.bank_account_id", store=True
    )
    branch = fields.Char("Branch")
    date = fields.Date("Date", default=fields.Date.context_today)
    ac_payee = fields.Boolean("A/C Payee", default=True)
    amount = fields.Float("Amount")
    remarks = fields.Text("Remarks")
    is_cheque_already_added_ids = fields.Many2many(
        "cheque.book.lines",
        string="Cheques",
        compute="_compute_cheque_already_added",
        store=True,
    )

    @api.depends("wizard_id", "wizard_id.is_cheque_already_added_ids")
    def _compute_cheque_already_added(self):
        for rec in self:
            rec.is_cheque_already_added_ids = rec.wizard_id.is_cheque_already_added_ids

    @api.onchange("wizard_id")
    def _onchange_wizard_id(self):
        if self.wizard_id:
            self.amount = self.wizard_id.amount
        else:
            self.amount = 0.0

    @api.constrains("amount")
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0.0:
                raise UserError(
                    _(
                        "Amount must be greater than 0 in cheque line %s .",
                        rec.cheque_id,
                    )
                )


class WizardInboundChequeLine(models.TransientModel):
    _name = "wizard.inbound.cheque.lines"
    _description = "Inbound Cheque Lines"

    wizard_id = fields.Many2one("account.payment.register", "Wizard")
    journal_id = fields.Many2one(
        related="wizard_id.journal_id", store=True, index=True, copy=False
    )
    payment_type = fields.Selection(
        [
            ("outbound", "Send Money"),
            ("inbound", "Receive Money"),
        ],
        string="Payment Type",
        related="wizard_id.payment_type",
        store=True,
    )
    cheque_id = fields.Char("Cheque")
    bank_account_id = fields.Many2one("res.bank", "Bank")
    branch = fields.Char("Branch")
    date = fields.Date("Date", default=fields.Date.context_today)
    ac_payee = fields.Boolean("A/C Payee", default=True)
    amount = fields.Float("Amount")
    remarks = fields.Text("Remarks")

    @api.onchange("wizard_id")
    def _onchange_wizard_id(self):
        if self.wizard_id:
            self.amount = self.wizard_id.amount
        else:
            self.amount = 0.0

    @api.constrains("amount")
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0.0:
                raise UserError(
                    _(
                        "Amount must be greater than 0 in cheque line %s .",
                        rec.cheque_id,
                    )
                )
