from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountPartnerSettlement(models.Model):
    _name = "account.partner.settlement"
    _description = "Partner Settlement"
    _order = "date desc, id desc"

    name = fields.Char(string="Settlement No.", required=True, copy=False, default="New", readonly=True)
    partner_id = fields.Many2one("res.partner", string="Partner", required=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        readonly=True,
    )
    currency_id = fields.Many2one(related="company_id.currency_id", string="Currency", readonly=True)
    date = fields.Date(string="Settlement Date", required=True, default=fields.Date.context_today)
    journal_id = fields.Many2one(
        "account.journal",
        string="Settlement Journal",
        required=True,
        domain="[('type', '=', 'general'), ('company_id', '=', company_id)]",
    )
    line_ids = fields.One2many("account.partner.settlement.line", "settlement_id", string="Documents")
    invoice_total = fields.Monetary(string="Selected Customer Invoice Total", compute="_compute_totals", store=True)
    bill_total = fields.Monetary(string="Selected Vendor Bill Total", compute="_compute_totals", store=True)
    settlement_amount = fields.Monetary(string="Settlement Amount", compute="_compute_totals", store=True)
    invoice_refs = fields.Char(string="Invoice References", compute="_compute_reference_fields", store=True)
    bill_refs = fields.Char(string="Bill References", compute="_compute_reference_fields", store=True)
    settlement_move_id = fields.Many2one("account.move", string="Settlement Journal Entry", readonly=True, copy=False)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("done", "Done"),
        ],
        string="Status",
        default="draft",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("account.partner.settlement") or "New"
        return super().create(vals_list)

    @api.depends("line_ids.is_selected", "line_ids.amount_to_settle", "line_ids.document_kind")
    def _compute_totals(self):
        for settlement in self:
            invoice_lines = settlement.line_ids.filtered(
                lambda line: line.is_selected and line.document_kind == "customer_invoice"
            )
            bill_lines = settlement.line_ids.filtered(
                lambda line: line.is_selected and line.document_kind == "vendor_bill"
            )
            settlement.invoice_total = sum(invoice_lines.mapped("amount_to_settle"))
            settlement.bill_total = sum(bill_lines.mapped("amount_to_settle"))
            settlement.settlement_amount = min(settlement.invoice_total, settlement.bill_total)

    @api.depends("line_ids.is_selected", "line_ids.amount_to_settle", "line_ids.move_id")
    def _compute_reference_fields(self):
        for settlement in self:
            invoices = settlement.line_ids.filtered(
                lambda line: line.is_selected and line.amount_to_settle and line.document_kind == "customer_invoice"
            ).mapped("move_id.name")
            bills = settlement.line_ids.filtered(
                lambda line: line.is_selected and line.amount_to_settle and line.document_kind == "vendor_bill"
            ).mapped("move_id.name")
            settlement.invoice_refs = ", ".join(invoices)
            settlement.bill_refs = ", ".join(bills)

    @api.constrains("journal_id")
    def _check_journal_type(self):
        for settlement in self:
            if settlement.journal_id and settlement.journal_id.type != "general":
                raise ValidationError(_("Settlement journal must be a miscellaneous journal."))

    def unlink(self):
        for settlement in self:
            if settlement.state == "done":
                raise UserError(_("Done settlements cannot be deleted."))
        return super().unlink()

    def _get_open_lines_for_move(self, move, document_kind):
        self.ensure_one()
        account_type = "asset_receivable" if document_kind == "customer_invoice" else "liability_payable"
        open_lines = move.line_ids.filtered(
            lambda line: line.account_type == account_type
            and not line.reconciled
            and line.partner_id == self.partner_id
        )
        if not open_lines:
            raise UserError(
                _("No open %s lines remain on document %s.")
                % ("receivable" if document_kind == "customer_invoice" else "payable", move.display_name)
            )
        accounts = open_lines.mapped("account_id")
        if len(accounts) != 1:
            raise UserError(
                _("Document %s has multiple open %s accounts and cannot be settled automatically.")
                % (move.display_name, "receivable" if document_kind == "customer_invoice" else "payable")
            )
        return open_lines

    def _prepare_reference_text(self, values, prefix):
        if not values:
            return ""
        if len(values) <= 3:
            return "%s: %s" % (prefix, ", ".join(values))
        return "%s: %s (+%s more)" % (prefix, ", ".join(values[:3]), len(values) - 3)

    def _validate_selected_lines(self, selected_lines):
        self.ensure_one()
        if not selected_lines:
            raise UserError(_("Please select at least one customer invoice and one vendor bill to settle."))

        if any(line.move_id.company_id != self.company_id for line in selected_lines):
            raise UserError(_("All selected documents must belong to the same company as the settlement."))

        foreign_currency_lines = selected_lines.filtered(lambda line: line.currency_id != self.currency_id)
        if foreign_currency_lines:
            raise UserError(_("This version supports only documents in the company currency."))

        not_posted = selected_lines.filtered(lambda line: line.move_id.state != "posted")
        if not_posted:
            raise UserError(_("All selected documents must be posted before settlement."))

    def action_load_open_documents(self):
        for settlement in self:
            if settlement.state != "draft":
                raise UserError(_("Only draft settlements can load documents."))
            if not settlement.partner_id:
                raise UserError(_("Please select a partner first."))

            lines_commands = [Command.clear()]
            document_specs = [
                ("customer_invoice", "out_invoice"),
                ("vendor_bill", "in_invoice"),
            ]
            for document_kind, move_type in document_specs:
                moves = self.env["account.move"].search(
                    [
                        ("move_type", "=", move_type),
                        ("state", "=", "posted"),
                        ("payment_state", "in", ("not_paid", "partial", "in_payment")),
                        ("partner_id", "=", settlement.partner_id.id),
                        ("company_id", "=", settlement.company_id.id),
                        ("amount_residual", ">", 0),
                    ],
                    order="invoice_date asc, id asc",
                )
                for move in moves:
                    open_lines = settlement._get_open_lines_for_move(move, document_kind)
                    lines_commands.append(
                        Command.create(
                            {
                                "move_id": move.id,
                                "document_kind": document_kind,
                                "currency_id": move.currency_id.id,
                                "account_id": open_lines[0].account_id.id,
                                "residual_amount": abs(sum(open_lines.mapped("amount_residual"))),
                                "amount_to_settle": 0.0,
                                "is_selected": True,
                            }
                        )
                    )
            settlement.line_ids = lines_commands
            settlement.action_recalculate()
        return True

    def action_recalculate(self):
        for settlement in self:
            if settlement.state != "draft":
                raise UserError(_("Only draft settlements can be recalculated."))

            lines = settlement.line_ids
            lines.write({"amount_to_settle": 0.0})

            selected_invoice_lines = lines.filtered(
                lambda line: line.is_selected and line.document_kind == "customer_invoice"
            ).sorted(key=lambda line: (line.document_date or fields.Date.today(), line.id))
            selected_bill_lines = lines.filtered(
                lambda line: line.is_selected and line.document_kind == "vendor_bill"
            ).sorted(key=lambda line: (line.document_date or fields.Date.today(), line.id))

            max_settlement = min(
                sum(selected_invoice_lines.mapped("residual_amount")),
                sum(selected_bill_lines.mapped("residual_amount")),
            )
            max_settlement = settlement.currency_id.round(max_settlement)

            remaining = max_settlement
            for line in selected_invoice_lines:
                amount = min(line.residual_amount, remaining)
                line.amount_to_settle = settlement.currency_id.round(amount)
                remaining = settlement.currency_id.round(remaining - amount)

            remaining = max_settlement
            for line in selected_bill_lines:
                amount = min(line.residual_amount, remaining)
                line.amount_to_settle = settlement.currency_id.round(amount)
                remaining = settlement.currency_id.round(remaining - amount)
        return True

    def action_select_all(self):
        self.ensure_one()
        if self.state != "draft":
            raise UserError(_("Only draft settlements can be modified."))
        self.line_ids.write({"is_selected": True})
        self.action_recalculate()
        return True

    def action_unselect_all(self):
        self.ensure_one()
        if self.state != "draft":
            raise UserError(_("Only draft settlements can be modified."))
        self.line_ids.write({"is_selected": False})
        self.action_recalculate()
        return True

    def action_post_settlement(self):
        for settlement in self:
            if settlement.state != "draft":
                raise UserError(_("Only draft settlements can be posted."))
            if settlement.settlement_move_id:
                raise UserError(_("A settlement journal entry has already been created."))
            if not settlement.journal_id:
                raise UserError(_("Please select a settlement journal."))

            settlement.action_recalculate()
            selected_lines = settlement.line_ids.filtered(lambda line: line.is_selected and line.amount_to_settle > 0)
            settlement._validate_selected_lines(selected_lines)

            invoice_lines = selected_lines.filtered(lambda line: line.document_kind == "customer_invoice")
            bill_lines = selected_lines.filtered(lambda line: line.document_kind == "vendor_bill")
            if not invoice_lines or not bill_lines:
                raise UserError(_("Settlement requires at least one customer invoice and one vendor bill."))

            debit_total = settlement.currency_id.round(sum(bill_lines.mapped("amount_to_settle")))
            credit_total = settlement.currency_id.round(sum(invoice_lines.mapped("amount_to_settle")))
            if debit_total != credit_total:
                raise UserError(_("Selected invoice and bill settlement amounts must be equal before posting."))

            invoice_refs = invoice_lines.mapped("move_id.name")
            bill_refs = bill_lines.mapped("move_id.name")
            reference_chunks = [
                settlement.name,
                settlement._prepare_reference_text(invoice_refs, "INV"),
                settlement._prepare_reference_text(bill_refs, "BILL"),
            ]
            move_ref = " | ".join(chunk for chunk in reference_chunks if chunk)
            narration = "\n".join(
                [
                    "Partner Settlement %s" % settlement.name,
                    "Partner: %s" % settlement.partner_id.display_name,
                    "Invoices: %s" % (", ".join(invoice_refs) or "-"),
                    "Bills: %s" % (", ".join(bill_refs) or "-"),
                ]
            )

            move_line_commands = []
            for line in bill_lines:
                move_line_commands.append(
                    Command.create(
                        {
                            "partner_id": settlement.partner_id.id,
                            "account_id": line.account_id.id,
                            "name": "Settlement Bill %s" % line.move_id.name,
                            "debit": line.amount_to_settle,
                            "credit": 0.0,
                        }
                    )
                )

            for line in invoice_lines:
                move_line_commands.append(
                    Command.create(
                        {
                            "partner_id": settlement.partner_id.id,
                            "account_id": line.account_id.id,
                            "name": "Settlement Invoice %s" % line.move_id.name,
                            "debit": 0.0,
                            "credit": line.amount_to_settle,
                        }
                    )
                )

            move = self.env["account.move"].create(
                {
                    "journal_id": settlement.journal_id.id,
                    "date": settlement.date,
                    "ref": move_ref,
                    "narration": narration,
                    "company_id": settlement.company_id.id,
                    "line_ids": move_line_commands,
                }
            )

            generated_pairs = []
            move_line_by_name = {
                line.name: line
                for line in move.line_ids.filtered(
                    lambda journal_line: journal_line.partner_id == settlement.partner_id
                    and journal_line.account_id in selected_lines.mapped("account_id")
                )
            }
            for line in bill_lines:
                generated_pairs.append((line, move_line_by_name["Settlement Bill %s" % line.move_id.name]))
            for line in invoice_lines:
                generated_pairs.append((line, move_line_by_name["Settlement Invoice %s" % line.move_id.name]))

            move.action_post()

            for line, generated_line in generated_pairs:
                open_lines = settlement._get_open_lines_for_move(line.move_id, line.document_kind)
                (open_lines | generated_line).reconcile()

            settlement.write(
                {
                    "settlement_move_id": move.id,
                    "state": "done",
                }
            )
        return True

    def action_view_journal_entry(self):
        self.ensure_one()
        if not self.settlement_move_id:
            raise UserError(_("No settlement journal entry has been created yet."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Settlement Journal Entry"),
            "res_model": "account.move",
            "res_id": self.settlement_move_id.id,
            "view_mode": "form",
            "target": "current",
        }


class AccountPartnerSettlementLine(models.Model):
    _name = "account.partner.settlement.line"
    _description = "Partner Settlement Line"
    _order = "document_date asc, id asc"

    settlement_id = fields.Many2one("account.partner.settlement", string="Settlement", required=True, ondelete="cascade")
    company_id = fields.Many2one(related="settlement_id.company_id", string="Company", store=True, readonly=True)
    partner_id = fields.Many2one(related="settlement_id.partner_id", string="Partner", store=True, readonly=True)
    document_kind = fields.Selection(
        [
            ("customer_invoice", "Customer Invoice"),
            ("vendor_bill", "Vendor Bill"),
        ],
        string="Document Type",
        required=True,
        readonly=True,
    )
    move_id = fields.Many2one("account.move", string="Document", required=True, readonly=True)
    currency_id = fields.Many2one("res.currency", string="Currency", required=True, readonly=True)
    account_id = fields.Many2one("account.account", string="GL Account", required=True, readonly=True)
    document_date = fields.Date(related="move_id.invoice_date", string="Document Date", store=True, readonly=True)
    residual_amount = fields.Monetary(string="Open Amount", currency_field="currency_id", readonly=True)
    amount_to_settle = fields.Monetary(string="Settlement Amount", currency_field="currency_id", readonly=True)
    is_selected = fields.Boolean(string="Selected", default=True)

    @api.constrains("residual_amount", "amount_to_settle")
    def _check_amounts(self):
        for line in self:
            if line.amount_to_settle < 0:
                raise ValidationError(_("Settlement amount cannot be negative."))
            if line.amount_to_settle - line.residual_amount > line.currency_id.rounding:
                raise ValidationError(_("Settlement amount cannot exceed the open amount."))
