from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    cross_settlement_line_ids = fields.One2many(
        "account.payment.register.cross.settlement.line",
        "wizard_id",
        string="Offset Documents",
    )
    cross_settlement_amount = fields.Monetary(
        string="Cross Settlement Amount",
        currency_field="currency_id",
        compute="_compute_cross_settlement_amount",
    )
    cross_settlement_partner_eligible = fields.Boolean(
        compute="_compute_cross_settlement_partner_eligible",
    )
    show_cross_settlement = fields.Boolean(
        compute="_compute_show_cross_settlement",
    )
    cross_settlement_amount_editable = fields.Boolean(
        compute="_compute_cross_settlement_amount_editable",
    )

    def _get_preserved_state_key(self):
        self.ensure_one()
        return self._origin.id or self.id

    @api.model
    def default_get(self, fields_list):
        required_fields = {
            "line_ids",
            "partner_id",
            "company_id",
            "partner_type",
            "currency_id",
            "cross_settlement_line_ids",
        }
        res = super().default_get(list(set(fields_list) | required_fields))
        seed = self._get_cross_settlement_seed_values(res)
        partner_id = seed["partner_id"]
        company_id = seed["company_id"]
        partner_type = seed["partner_type"]
        currency_id = seed["currency_id"]
        if partner_id:
            res["partner_id"] = partner_id
        if company_id:
            res["company_id"] = company_id
        if partner_type:
            res["partner_type"] = partner_type
        if currency_id:
            res["currency_id"] = currency_id
        if partner_id and company_id and partner_type and currency_id and self._is_cross_settlement_partner_eligible(
            self.env["res.partner"].browse(partner_id)
        ):
            res["cross_settlement_line_ids"] = self._prepare_default_cross_settlement_commands(
                partner_id=partner_id,
                company_id=company_id,
                partner_type=partner_type,
                currency_id=currency_id,
            )
        return res

    @api.model_create_multi
    def create(self, vals_list):
        sanitized_vals_list = []
        shadow_line_values_list = []
        for vals in vals_list:
            sanitized_vals = dict(vals)
            if sanitized_vals.get("settlement_journal_id") and not sanitized_vals.get("journal_id"):
                sanitized_vals["journal_id"] = sanitized_vals["settlement_journal_id"]
            sanitized_vals.pop("settlement_journal_id", None)
            shadow_line_values = []
            commands = sanitized_vals.get("cross_settlement_line_ids") or []
            sanitized_commands = []
            for command in commands:
                if not isinstance(command, (list, tuple)) or len(command) < 3 or command[0] != 0:
                    sanitized_commands.append(command)
                    continue
                line_vals = dict(command[2] or {})
                if line_vals.get("move_id"):
                    sanitized_commands.append((command[0], command[1], line_vals))
                    continue
                if line_vals:
                    shadow_line_values.append(line_vals)
            sanitized_commands = self._deduplicate_cross_settlement_commands(sanitized_commands)
            if shadow_line_values:
                hydrated_commands = self._hydrate_cross_settlement_shadow_commands(
                    sanitized_vals,
                    sanitized_commands,
                    shadow_line_values,
                )
                if hydrated_commands:
                    sanitized_vals["cross_settlement_line_ids"] = hydrated_commands
                    shadow_line_values = []
                elif sanitized_commands:
                    sanitized_vals["cross_settlement_line_ids"] = sanitized_commands
                else:
                    sanitized_vals.pop("cross_settlement_line_ids", None)
            sanitized_vals_list.append(sanitized_vals)
            shadow_line_values_list.append(shadow_line_values)

        wizards = super().create(sanitized_vals_list)
        for wizard, vals, shadow_line_values in zip(wizards, sanitized_vals_list, shadow_line_values_list):
            wizard._normalize_cross_settlement_lines()
            if not vals.get("cross_settlement_line_ids"):
                wizard._populate_cross_settlement_lines()
            if shadow_line_values:
                wizard._apply_cross_settlement_shadow_values(shadow_line_values)
        return wizards

    @api.depends(
        "cross_settlement_line_ids.is_selected",
        "cross_settlement_line_ids.amount_to_settle",
        "cross_settlement_line_ids.residual_signed_amount",
    )
    def _compute_cross_settlement_amount(self):
        for wizard in self:
            wizard.cross_settlement_amount = (
                wizard._get_effective_cross_settlement_amount() if wizard.currency_id else 0.0
            )

    @api.depends("partner_id", "cross_settlement_line_ids")
    def _compute_show_cross_settlement(self):
        for wizard in self:
            wizard.show_cross_settlement = bool(
                wizard.partner_id
                and wizard.cross_settlement_partner_eligible
                and wizard.company_id
                and wizard.partner_type
                and wizard.currency_id
            )

    @api.depends(
        "show_cross_settlement",
        "partner_id",
        "company_id",
        "currency_id",
        "line_ids",
        "line_ids.move_id",
        "line_ids.partner_id",
        "line_ids.company_id",
    )
    def _compute_cross_settlement_amount_editable(self):
        for wizard in self:
            if wizard.can_edit_wizard:
                wizard.cross_settlement_amount_editable = True
                continue
            current_moves = wizard.line_ids.move_id
            wizard.cross_settlement_amount_editable = bool(
                wizard.show_cross_settlement
                and current_moves
                and len(current_moves) == 1
                and len(current_moves.mapped("company_id")) == 1
                and len(current_moves.mapped("partner_id.commercial_partner_id")) == 1
                and len(current_moves.mapped("currency_id")) == 1
                and current_moves.company_id == wizard.company_id
                and current_moves.partner_id.commercial_partner_id == wizard.partner_id.commercial_partner_id
                and current_moves.currency_id == wizard.currency_id
            )

    @api.depends(
        "partner_id",
        "partner_id.is_customer",
        "partner_id.is_supplier",
        "partner_id.customer_rank",
        "partner_id.supplier_rank",
    )
    def _compute_cross_settlement_partner_eligible(self):
        for wizard in self:
            wizard.cross_settlement_partner_eligible = wizard._is_cross_settlement_partner_eligible()

    def _can_edit_payment_amount(self):
        self.ensure_one()
        return bool(self.can_edit_wizard or self.cross_settlement_amount_editable)

    @api.depends("early_payment_discount_mode")
    def _compute_payment_difference_handling(self):
        super()._compute_payment_difference_handling()
        for wizard in self:
            if wizard.payment_difference_handling:
                continue
            if not wizard.cross_settlement_amount_editable:
                continue
            wizard.payment_difference_handling = (
                "reconcile" if wizard.early_payment_discount_mode else "open"
            )

    @api.depends(
        "early_payment_discount_mode",
        "can_edit_wizard",
        "can_group_payments",
        "group_payment",
        "payment_method_line_id",
        "cross_settlement_amount_editable",
        "payment_difference",
    )
    def _compute_show_payment_difference(self):
        super()._compute_show_payment_difference()
        for wizard in self:
            if wizard.show_payment_difference:
                continue
            wizard.show_payment_difference = bool(
                wizard.payment_difference != 0.0
                and not wizard.early_payment_discount_mode
                and wizard.cross_settlement_amount_editable
                and (not wizard.can_group_payments or wizard.group_payment)
                and wizard.payment_method_line_id.payment_account_id
            )

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
        "cross_settlement_line_ids.is_selected",
        "cross_settlement_line_ids.amount_to_settle",
    )
    def _compute_amount(self):
        preserved_manual_states = {}
        for wizard in self:
            if not wizard._can_edit_payment_amount() or not wizard.cross_settlement_amount:
                continue
            if not wizard.custom_user_amount:
                continue
            preserved_manual_states[wizard._get_preserved_state_key()] = {
                "amount": wizard.custom_user_amount,
                "handling": wizard.payment_difference_handling,
                "currency_id": wizard.custom_user_currency_id.id if wizard.custom_user_currency_id else False,
            }
        super()._compute_amount()
        for wizard in self:
            if not wizard.journal_id or not wizard.currency_id:
                continue
            preserved_state = preserved_manual_states.get(wizard._get_preserved_state_key())
            if preserved_state:
                target_amount = wizard._sync_allocation_lines_to_target_amount(preserved_state["amount"])
                if wizard.currency_id.compare_amounts(wizard.amount, target_amount) != 0:
                    wizard.amount = target_amount
                wizard.custom_user_amount = preserved_state["amount"]
                wizard.custom_user_currency_id = preserved_state["currency_id"] or wizard.currency_id
                if (
                    preserved_state["handling"]
                    and wizard.payment_difference_handling != preserved_state["handling"]
                ):
                    wizard.payment_difference_handling = preserved_state["handling"]
                wizard._cleanup_cross_settlement_auto_deductions()
                continue
            if wizard.custom_user_amount:
                continue
            wizard._apply_single_wht_amount_if_needed()
            if not wizard.cross_settlement_amount:
                continue
            wizard.amount = wizard.currency_id.round(max(wizard.amount - wizard.cross_settlement_amount, 0.0))

    @api.depends(
        "can_edit_wizard",
        "amount",
        "installments_mode",
        "manual_currency_rate",
        "manual_currency_rate_active",
        "currency_id",
        "source_currency_id",
        "source_amount_currency",
        "cross_settlement_line_ids.is_selected",
        "cross_settlement_line_ids.amount_to_settle",
    )
    def _compute_payment_difference(self):
        super()._compute_payment_difference()
        for wizard in self:
            if not wizard.payment_date:
                continue
            base_difference = wizard._get_base_difference_before_cross_settlement()
            wizard.payment_difference = wizard._get_cross_adjusted_difference(base_difference)

    @api.onchange("cross_settlement_line_ids")
    def _onchange_cross_settlement_line_ids(self):
        for wizard in self:
            wizard._apply_cross_settlement_selection()

    @api.onchange("amount")
    def _onchange_amount(self):
        manual_cross_amounts = {}
        for wizard in self:
            if wizard.cross_settlement_amount and wizard._can_edit_payment_amount():
                manual_cross_amounts[wizard._get_preserved_state_key()] = wizard.amount
                wizard.custom_user_amount = wizard.amount
                wizard.custom_user_currency_id = wizard.currency_id
        res = super()._onchange_amount()
        for wizard in self:
            if not wizard._should_sync_allocation_lines():
                continue
            target_seed_amount = manual_cross_amounts.get(wizard._get_preserved_state_key(), wizard.amount)
            target_amount = wizard._sync_allocation_lines_to_target_amount(target_seed_amount)
            if wizard.currency_id.compare_amounts(wizard.amount, target_amount) != 0:
                wizard.amount = target_amount
        return res

    @api.onchange("payment_difference", "cross_settlement_line_ids", "deduction_ids")
    def _onchange_cleanup_cross_settlement_auto_deductions(self):
        for wizard in self:
            wizard._cleanup_cross_settlement_auto_deductions()

    def action_select_all(self):
        self.ensure_one()
        self.cross_settlement_line_ids.write({"is_selected": True})
        self._apply_cross_settlement_selection()
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_unselect_all(self):
        self.ensure_one()
        self.cross_settlement_line_ids.write({"is_selected": False})
        self._apply_cross_settlement_selection()
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    @api.onchange("partner_id", "company_id", "partner_type", "currency_id")
    def _onchange_cross_settlement_seed_fields(self):
        for wizard in self:
            wizard._refresh_cross_settlement_lines()

    def _get_current_account_type(self):
        self.ensure_one()
        return "asset_receivable" if self.partner_type == "customer" else "liability_payable"

    @api.model
    def _get_cross_settlement_seed_values(self, values=None):
        values = values or {}
        partner_id = values.get("partner_id")
        company_id = values.get("company_id")
        partner_type = values.get("partner_type")
        currency_id = values.get("currency_id")
        active_model = self.env.context.get("active_model")
        active_ids = self.env.context.get("active_ids") or []
        if active_model not in ("account.move", "account.move.line") or not active_ids:
            return {
                "partner_id": partner_id,
                "company_id": company_id,
                "partner_type": partner_type,
                "currency_id": currency_id,
            }
        if active_model == "account.move.line":
            moves = self.env["account.move.line"].browse(active_ids).exists().mapped("move_id")
        else:
            moves = self.env["account.move"].browse(active_ids).exists()
        if not moves:
            return {
                "partner_id": partner_id,
                "company_id": company_id,
                "partner_type": partner_type,
                "currency_id": currency_id,
            }
        partners = moves.mapped("partner_id")
        companies = moves.mapped("company_id")
        currencies = moves.mapped("currency_id")
        if not partner_id and len(partners) == 1:
            partner_id = partners.id
        if not company_id and len(companies) == 1:
            company_id = companies.id
        if not currency_id and len(currencies) == 1:
            currency_id = currencies.id
        if not partner_type and len(moves) == 1:
            partner_type = "customer" if moves.move_type in ("out_invoice", "out_refund") else "supplier"
        return {
            "partner_id": partner_id,
            "company_id": company_id,
            "partner_type": partner_type,
            "currency_id": currency_id,
        }

    def _is_cross_settlement_partner_eligible(self, partner=None):
        partner = (partner or self.partner_id).commercial_partner_id
        if not partner:
            return False
        has_customer = False
        has_supplier = False
        if "is_customer" in partner._fields:
            has_customer = bool(partner.is_customer)
        elif "customer_rank" in partner._fields:
            has_customer = partner.customer_rank > 0
        if "is_supplier" in partner._fields:
            has_supplier = bool(partner.is_supplier)
        elif "supplier_rank" in partner._fields:
            has_supplier = partner.supplier_rank > 0
        return has_customer and has_supplier

    def _get_opposite_account_type(self):
        self.ensure_one()
        return "liability_payable" if self.partner_type == "customer" else "asset_receivable"

    def _get_opposite_move_types(self):
        self.ensure_one()
        if self.partner_type == "customer":
            return ("in_invoice", "in_refund")
        return ("out_invoice", "out_refund")

    def _get_open_move_lines(self, move, account_type):
        self.ensure_one()
        open_lines = move.line_ids.filtered(
            lambda line: line.account_type == account_type
            and not line.reconciled
            and line.partner_id.commercial_partner_id == self.partner_id.commercial_partner_id
        )
        if not open_lines:
            return self.env["account.move.line"]
        accounts = open_lines.mapped("account_id")
        if len(accounts) != 1:
            raise UserError(
                _("Document %s has multiple open %s accounts and cannot be settled automatically.")
                % (move.display_name, "receivable" if account_type == "asset_receivable" else "payable")
            )
        return open_lines

    def _get_signed_open_amount(self, open_lines, account_type):
        self.ensure_one()
        raw_amount = sum(open_lines.mapped("amount_residual"))
        signed_amount = raw_amount if account_type == "asset_receivable" else -raw_amount
        return self.currency_id.round(signed_amount)

    def _prepare_default_cross_settlement_commands(self, partner_id, company_id, partner_type, currency_id):
        partner = self.env["res.partner"].browse(partner_id)
        if not self._is_cross_settlement_partner_eligible(partner):
            return []
        currency = self.env["res.currency"].browse(currency_id)
        account_type = "liability_payable" if partner_type == "customer" else "asset_receivable"
        move_types = ("in_invoice", "in_refund") if partner_type == "customer" else ("out_invoice", "out_refund")
        active_ids = set(self.env.context.get("active_ids", []))
        moves = self.env["account.move"].search(
            [
                ("company_id", "=", company_id),
                ("partner_id", "=", partner.id),
                ("state", "=", "posted"),
                ("move_type", "in", move_types),
            ],
            order="invoice_date asc, id asc",
        )
        commands = []
        seen_move_ids = set()
        for move in moves:
            if move.id in seen_move_ids:
                continue
            if move.id in active_ids:
                continue
            if move.currency_id != currency:
                continue
            open_lines = move.line_ids.filtered(
                lambda line: line.account_type == account_type
                and not line.reconciled
                and line.partner_id.commercial_partner_id == partner.commercial_partner_id
            )
            if not open_lines:
                continue
            accounts = open_lines.mapped("account_id")
            if len(accounts) != 1:
                continue
            signed_amount = self.env.company.currency_id.round(
                sum(open_lines.mapped("amount_residual")) if account_type == "asset_receivable" else -sum(open_lines.mapped("amount_residual"))
            )
            if currency.is_zero(signed_amount):
                continue
            commands.append(
                Command.create(
                    {
                        "move_id": move.id,
                        "currency_id": currency.id,
                        "account_id": accounts.id,
                        "residual_signed_amount": signed_amount,
                        "amount_to_settle": 0.0,
                        "is_selected": False,
                    }
                )
            )
            seen_move_ids.add(move.id)
        return commands

    def _prepare_existing_cross_settlement_command(self, line):
        values = {
            "move_id": line.move_id.id,
            "currency_id": line.currency_id.id,
            "account_id": line.account_id.id,
            "residual_signed_amount": line.residual_signed_amount,
            "amount_to_settle": line.amount_to_settle,
            "is_selected": line.is_selected,
        }
        return Command.create(values)

    @api.model
    def _deduplicate_cross_settlement_commands(self, commands):
        if not commands:
            return commands
        deduplicated_commands = []
        command_by_move = {}
        for command in commands:
            if not isinstance(command, (list, tuple)) or len(command) < 3 or command[0] != 0:
                deduplicated_commands.append(command)
                continue
            line_vals = dict(command[2] or {})
            move_id = line_vals.get("move_id")
            if not move_id:
                deduplicated_commands.append(command)
                continue
            existing_vals = command_by_move.get(move_id)
            if not existing_vals:
                command_by_move[move_id] = line_vals
                deduplicated_commands.append(Command.create(line_vals))
                continue
            existing_vals["is_selected"] = existing_vals.get("is_selected") or line_vals.get("is_selected")
            existing_vals["amount_to_settle"] = max(
                existing_vals.get("amount_to_settle") or 0.0,
                line_vals.get("amount_to_settle") or 0.0,
            )
            existing_vals["currency_id"] = existing_vals.get("currency_id") or line_vals.get("currency_id")
            existing_vals["account_id"] = existing_vals.get("account_id") or line_vals.get("account_id")
            existing_vals["residual_signed_amount"] = (
                existing_vals.get("residual_signed_amount")
                if existing_vals.get("residual_signed_amount") is not None
                else line_vals.get("residual_signed_amount")
            )
        return deduplicated_commands

    @api.model
    def _hydrate_cross_settlement_shadow_commands(self, sanitized_vals, sanitized_commands, shadow_line_values):
        seed = self._get_cross_settlement_seed_values(sanitized_vals)
        partner_id = seed.get("partner_id")
        company_id = seed.get("company_id")
        partner_type = seed.get("partner_type")
        currency_id = seed.get("currency_id")
        if not (partner_id and company_id and partner_type and currency_id):
            return sanitized_commands

        partner = self.env["res.partner"].browse(partner_id)
        if not self._is_cross_settlement_partner_eligible(partner):
            return sanitized_commands

        hydrated_commands = list(
            self._prepare_default_cross_settlement_commands(
                partner_id=partner_id,
                company_id=company_id,
                partner_type=partner_type,
                currency_id=currency_id,
            )
        )
        if not hydrated_commands:
            return sanitized_commands

        ordered_move_ids = []
        command_by_move_id = {}
        for command in hydrated_commands:
            if not isinstance(command, (list, tuple)) or len(command) < 3 or command[0] != 0:
                continue
            line_vals = dict(command[2] or {})
            move_id = line_vals.get("move_id")
            if not move_id:
                continue
            ordered_move_ids.append(move_id)
            command_by_move_id[move_id] = line_vals

        for index, shadow_vals in enumerate(shadow_line_values):
            if index >= len(ordered_move_ids):
                break
            line_vals = command_by_move_id.get(ordered_move_ids[index])
            if not line_vals:
                continue
            if "is_selected" in shadow_vals:
                line_vals["is_selected"] = shadow_vals["is_selected"]
            if "amount_to_settle" in shadow_vals and shadow_vals["amount_to_settle"] is not None:
                line_vals["amount_to_settle"] = shadow_vals["amount_to_settle"]

        for command in sanitized_commands:
            if not isinstance(command, (list, tuple)) or len(command) < 3 or command[0] != 0:
                continue
            line_vals = dict(command[2] or {})
            move_id = line_vals.get("move_id")
            if not move_id:
                continue
            command_by_move_id[move_id] = line_vals
            if move_id not in ordered_move_ids:
                ordered_move_ids.append(move_id)

        return [
            Command.create(command_by_move_id[move_id])
            for move_id in ordered_move_ids
            if move_id in command_by_move_id
        ]

    def _populate_cross_settlement_lines(self):
        for wizard in self:
            if (
                not wizard.partner_id
                or not wizard.company_id
                or not wizard.partner_type
                or not wizard.cross_settlement_partner_eligible
                or wizard.cross_settlement_line_ids
            ):
                continue
            commands = wizard._prepare_default_cross_settlement_commands(
                partner_id=wizard.partner_id.id,
                company_id=wizard.company_id.id,
                partner_type=wizard.partner_type,
                currency_id=wizard.currency_id.id,
            )
            if commands:
                wizard.write({"cross_settlement_line_ids": commands})
                wizard._normalize_cross_settlement_lines()

    def _apply_cross_settlement_shadow_values(self, shadow_line_values):
        self.ensure_one()
        if not shadow_line_values or not self.cross_settlement_line_ids:
            return
        ordered_lines = self.cross_settlement_line_ids
        touched = False
        for line, shadow_vals in zip(ordered_lines, shadow_line_values):
            updates = {}
            if "is_selected" in shadow_vals:
                updates["is_selected"] = shadow_vals["is_selected"]
            if "amount_to_settle" in shadow_vals and shadow_vals["amount_to_settle"] is not None:
                updates["amount_to_settle"] = shadow_vals["amount_to_settle"]
            if updates:
                line.write(updates)
                touched = True
        if touched:
            self._apply_cross_settlement_selection()

    def _refresh_cross_settlement_lines(self):
        for wizard in self:
            if not wizard.cross_settlement_partner_eligible or not wizard.partner_id or not wizard.company_id or not wizard.partner_type or not wizard.currency_id:
                wizard.update({"cross_settlement_line_ids": [Command.clear()]})
                continue
            commands = wizard._prepare_default_cross_settlement_commands(
                partner_id=wizard.partner_id.id,
                company_id=wizard.company_id.id,
                partner_type=wizard.partner_type,
                currency_id=wizard.currency_id.id,
            )
            wizard.update({"cross_settlement_line_ids": [Command.clear(), *commands] if commands else [Command.clear()]})

    def _normalize_cross_settlement_lines(self):
        self.ensure_one()
        if len(self.cross_settlement_line_ids) <= 1:
            return
        unique_lines = []
        seen_move_ids = set()
        duplicates_found = False
        for line in self.cross_settlement_line_ids:
            move_id = line.move_id.id
            if move_id not in seen_move_ids:
                unique_lines.append(line)
                seen_move_ids.add(move_id)
                continue
            duplicates_found = True
            target = next(existing for existing in unique_lines if existing.move_id.id == move_id)
            target.is_selected = target.is_selected or line.is_selected
            target.amount_to_settle = max(target.amount_to_settle, line.amount_to_settle)
        if not duplicates_found:
            return
        commands = [Command.clear()]
        commands.extend(self._prepare_existing_cross_settlement_command(line) for line in unique_lines)
        self.update({"cross_settlement_line_ids": commands})

    def _get_base_settle_capacity(self):
        self.ensure_one()
        total_amount_values = self._get_total_amounts_to_pay(self.batches)
        return self.currency_id.round(total_amount_values["amount_by_default"])

    def _get_effective_cross_settlement_amount(self):
        self.ensure_one()
        if not self.currency_id:
            return 0.0
        selected_lines = self.cross_settlement_line_ids.filtered("is_selected")
        if not selected_lines:
            return 0.0

        explicit_total = 0.0
        has_explicit_amount = False
        for line in selected_lines:
            if not line.amount_to_settle:
                continue
            has_explicit_amount = True
            signed_amount = line.amount_to_settle
            if line.residual_signed_amount < 0:
                signed_amount *= -1
            explicit_total += signed_amount
        if has_explicit_amount:
            return self.currency_id.round(max(explicit_total, 0.0))

        selected_net = sum(selected_lines.mapped("residual_signed_amount"))
        if self.currency_id.compare_amounts(selected_net, 0.0) <= 0:
            return 0.0
        return self.currency_id.round(
            max(min(self._get_base_settle_capacity(), selected_net), 0.0)
        )

    def _should_sync_allocation_lines(self):
        self.ensure_one()
        return bool(
            self.currency_id
            and "allocation_line_ids" in self._fields
            and getattr(self, "allocation_line_ids", False)
        )

    def _get_allocation_target_bounds(self):
        self.ensure_one()
        if not self._should_sync_allocation_lines():
            return 0.0, 0.0
        minimum_target = self.currency_id.round(
            sum(
                self.allocation_line_ids.filtered(
                    lambda line: self.currency_id.compare_amounts(line.amount_residual_original, 0.0) < 0
                ).mapped("amount_residual_original")
            )
        )
        maximum_target = self.currency_id.round(sum(self.allocation_line_ids.mapped("amount_residual_original")))
        return minimum_target, maximum_target

    def _sync_allocation_lines_to_target_amount(self, target_amount=None):
        self.ensure_one()
        if not self._should_sync_allocation_lines():
            return target_amount if target_amount is not None else self.amount
        minimum_target, maximum_target = self._get_allocation_target_bounds()
        target_amount = self.currency_id.round(target_amount if target_amount is not None else self.amount or 0.0)
        if self.currency_id.compare_amounts(target_amount, minimum_target) < 0:
            target_amount = minimum_target
        if self.currency_id.compare_amounts(target_amount, maximum_target) > 0:
            target_amount = maximum_target
        remaining_reduction = self.currency_id.round(maximum_target - target_amount)
        for allocation in self.allocation_line_ids:
            amount_to_pay = allocation.amount_residual_original
            if (
                self.currency_id.compare_amounts(amount_to_pay, 0.0) > 0
                and self.currency_id.compare_amounts(remaining_reduction, 0.0) > 0
            ):
                reduction = min(amount_to_pay, remaining_reduction)
                amount_to_pay = self.currency_id.round(amount_to_pay - reduction)
                remaining_reduction = self.currency_id.round(remaining_reduction - reduction)
            allocation.amount_to_pay = amount_to_pay
            allocation.amount_residual = self.currency_id.round(allocation.amount_residual_original - amount_to_pay)
        return target_amount

    def _refresh_allocation_amount(self):
        tracked_amounts = {}
        for wizard in self:
            if wizard._should_sync_allocation_lines():
                tracked_amounts[wizard._get_preserved_state_key()] = wizard.amount
        result = super()._refresh_allocation_amount()
        for wizard in self:
            target_amount = tracked_amounts.get(wizard._get_preserved_state_key())
            if target_amount is None:
                continue
            synced_target = wizard._sync_allocation_lines_to_target_amount(target_amount)
            if wizard.currency_id and wizard.currency_id.compare_amounts(wizard.amount, synced_target) != 0:
                wizard.amount = synced_target
        return result

    def _apply_single_wht_amount_if_needed(self):
        self.ensure_one()
        if "wht_tax_id" not in self._fields or "wht_amount_base" not in self._fields:
            return
        if not self.wht_tax_id or not self.wht_amount_base:
            return
        if self.payment_difference_handling != "reconcile":
            return
        if getattr(self, "deduction_ids", False) and any(
            getattr(deduction, "wht_tax_id", False) for deduction in self.deduction_ids
        ):
            return
        if self.wht_tax_id.is_pit:
            self._onchange_pit()
        else:
            self._onchange_wht()

    def _has_parent_wht_base_payment_amount(self):
        self.ensure_one()
        return bool(getattr(super(AccountPaymentRegister, self), "_get_base_payment_amount_for_wht", None))

    def _get_base_payment_amount_for_wht(self):
        parent = getattr(super(), "_get_base_payment_amount_for_wht", None)
        if not parent:
            base_residual = self.currency_id.round(abs((self.amount or 0.0) + (self.payment_difference or 0.0)))
            return base_residual, base_residual
        return parent()

    def _get_base_difference_before_cross_settlement(self):
        self.ensure_one()
        if self._has_parent_wht_base_payment_amount():
            base_residual, _original = self._get_base_payment_amount_for_wht()
            return self.currency_id.round(max(base_residual - self.amount, 0.0))
        return self.payment_difference

    def _get_cross_adjusted_difference(self, base_difference):
        self.ensure_one()
        effective_cross_settlement_amount = self._get_effective_cross_settlement_amount()
        if not effective_cross_settlement_amount:
            return base_difference
        return self.currency_id.round(max(base_difference - effective_cross_settlement_amount, 0.0))

    def _allow_custom_user_amount_for_wht(self):
        allowed = False
        parent_allow = getattr(super(), "_allow_custom_user_amount_for_wht", None)
        if parent_allow:
            allowed = parent_allow()
        if allowed:
            return True
        self.ensure_one()
        if not self.cross_settlement_line_ids.filtered("is_selected"):
            return False
        return bool(
            getattr(self, "custom_user_amount", False)
            and self.payment_difference_handling in ("open", "reconcile", "reconcile_multi_deduct")
        )

    def _get_cross_expected_deduction_amount(self):
        self.ensure_one()
        full_residual, _original = self._get_base_payment_amount_for_wht()
        return self._get_cross_adjusted_difference(full_residual - self.amount)

    def _get_auto_difference_account(self):
        self.ensure_one()
        return getattr(self.company_id, "auto_diff_account_id", False)

    def _is_auto_difference_deduction_line(self, deduction):
        auto_account = self._get_auto_difference_account()
        return bool(auto_account and deduction.account_id == auto_account)

    def _prepare_existing_deduction_command(self, deduction):
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
            values["wht_tax_id"] = deduction.wht_tax_id.id or False
        if "wht_amount_base" in deduction._fields:
            values["wht_amount_base"] = deduction.wht_amount_base or 0.0
        return Command.create(values)

    def _get_effective_deduction_lines(self):
        self.ensure_one()
        auto_lines = self.deduction_ids.filtered(self._is_auto_difference_deduction_line)
        if not auto_lines:
            return self.deduction_ids
        keep_lines = self.deduction_ids - auto_lines
        expected_diff = self._get_cross_expected_deduction_amount()
        keep_total = sum(keep_lines.mapped("amount"))
        if self.currency_id.compare_amounts(expected_diff, keep_total) == 0:
            return keep_lines
        return self.deduction_ids

    def _cleanup_cross_settlement_auto_deductions(self):
        self.ensure_one()
        if not self.deduction_ids:
            return
        auto_lines = self.deduction_ids.filtered(self._is_auto_difference_deduction_line)
        if not auto_lines:
            return
        keep_lines = self.deduction_ids - auto_lines
        expected_diff = self._get_cross_expected_deduction_amount()
        keep_total = sum(keep_lines.mapped("amount"))
        if self.currency_id.compare_amounts(expected_diff, keep_total) != 0:
            return
        commands = [Command.clear()]
        commands.extend(self._prepare_existing_deduction_command(line) for line in keep_lines)
        values = {"deduction_ids": commands}
        if not keep_lines and self.payment_difference_handling == "reconcile_multi_deduct":
            values["payment_difference_handling"] = "open"
        self.update(values)

    def _validate_effective_deduction_balance(self):
        self.ensure_one()
        if self.payment_difference_handling != "reconcile_multi_deduct":
            return
        if self._get_wht_source_lines() and not self.deduction_ids:
            return
        if getattr(self, "manual_currency_rate_active", False) and getattr(self, "manual_currency_rate", 0.0):
            return
        total_deduction = sum(self._get_effective_deduction_lines().mapped("amount"))
        expected_diff = self._get_cross_expected_deduction_amount()
        if self.currency_id.compare_amounts(expected_diff, total_deduction) != 0:
            raise UserError(_("The total deduction should be %s") % expected_diff)

    def _get_document_label(self, move):
        self.ensure_one()
        if move.move_type in ("out_refund", "in_refund"):
            return "CN"
        if move.debit_origin_id:
            return "DN"
        if move.move_type == "out_invoice":
            return "Invoice"
        if move.move_type == "in_invoice":
            return "Bill"
        return move.move_type or "Document"

    def _get_document_reference(self, move):
        self.ensure_one()
        return "%s %s" % (self._get_document_label(move), move.name)

    def _get_settlement_line_name(self, move):
        self.ensure_one()
        return "Settlement %s" % self._get_document_reference(move)

    def _apply_cross_settlement_selection(self):
        self.ensure_one()
        if not self.currency_id:
            return
        base_cash_amount = self.currency_id.round(
            self.amount + self._get_effective_cross_settlement_amount()
        )
        self._normalize_cross_settlement_lines()
        for line in self.cross_settlement_line_ids:
            line.amount_to_settle = 0.0

        selected_lines = self.cross_settlement_line_ids.filtered("is_selected")
        if not selected_lines:
            target_amount = self._sync_allocation_lines_to_target_amount(base_cash_amount)
            if self.currency_id.compare_amounts(self.amount, target_amount) != 0:
                self.amount = target_amount
            return

        positive_lines = selected_lines.filtered(lambda line: line.residual_signed_amount > 0)
        negative_lines = selected_lines.filtered(lambda line: line.residual_signed_amount < 0)

        selected_net = sum(selected_lines.mapped("residual_signed_amount"))
        if self.currency_id.compare_amounts(selected_net, 0.0) <= 0:
            target_amount = self._sync_allocation_lines_to_target_amount(base_cash_amount)
            if self.currency_id.compare_amounts(self.amount, target_amount) != 0:
                self.amount = target_amount
            return

        target_amount = min(self._get_base_settle_capacity(), selected_net)
        negative_total = sum(negative_lines.mapped("residual_signed_amount"))

        for line in negative_lines:
            line.amount_to_settle = abs(line.residual_signed_amount)

        remaining_positive = target_amount - negative_total
        for line in positive_lines:
            amount = min(line.residual_signed_amount, remaining_positive)
            amount = self.currency_id.round(max(amount, 0.0))
            line.amount_to_settle = amount
            remaining_positive = self.currency_id.round(remaining_positive - amount)
            if self.currency_id.compare_amounts(remaining_positive, 0.0) <= 0:
                break

        cash_amount = self.currency_id.round(max(base_cash_amount - self.cross_settlement_amount, 0.0))
        cash_amount = self._sync_allocation_lines_to_target_amount(cash_amount)
        if self.currency_id.compare_amounts(self.amount, cash_amount) != 0:
            self.amount = cash_amount

    def _get_created_payment_records(self, action_result):
        payment_obj = self.env["account.payment"]
        if not isinstance(action_result, dict) or action_result.get("res_model") != "account.payment":
            return payment_obj
        if action_result.get("res_id"):
            return payment_obj.browse(action_result["res_id"]).exists()
        domain = action_result.get("domain")
        return payment_obj.search(domain) if domain else payment_obj

    def _validate_cross_settlement_inputs(self):
        self.ensure_one()
        selected_lines = self.cross_settlement_line_ids.filtered(
            lambda line: line.is_selected and line.amount_to_settle > 0
        )
        if not selected_lines:
            return selected_lines
        if not self.cross_settlement_partner_eligible:
            raise UserError(
                _(
                    "Cross settlement is available only when the contact is marked as both Is a Customer and Is a Supplier."
                )
            )
        if not self.journal_id:
            raise UserError(_("Please select a payment journal before creating the payment."))
        if any(line.move_id.company_id != self.company_id for line in selected_lines):
            raise UserError(_("All selected settlement documents must belong to the same company."))
        if any(line.currency_id != self.currency_id for line in selected_lines):
            raise UserError(_("All selected settlement documents must be in the payment currency."))
        return selected_lines

    def _is_cheque_payment_method_line(self, payment_method_line):
        self.ensure_one()
        return bool(
            payment_method_line
            and (
                getattr(payment_method_line, "is_cheque_incoming_line", False)
                or getattr(payment_method_line, "is_cheque_outgoing_line", False)
            )
        )

    def _get_non_cheque_payment_method_line(self):
        self.ensure_one()
        payment_method_line_obj = self.env["account.payment.method.line"]
        available_lines = payment_method_line_obj
        if self.journal_id:
            if self.payment_type == "inbound":
                available_lines = self.journal_id.inbound_payment_method_line_ids
            else:
                available_lines = self.journal_id.outbound_payment_method_line_ids
        non_cheque_lines = available_lines.filtered(
            lambda line: not self._is_cheque_payment_method_line(line)
        )
        if not non_cheque_lines:
            candidate_lines = payment_method_line_obj.search(
                [
                    ("journal_id.company_id", "=", self.company_id.id),
                    ("journal_id.type", "in", ("bank", "cash")),
                    ("payment_type", "=", self.payment_type),
                ]
            ).filtered(lambda line: not self._is_cheque_payment_method_line(line))
            non_cheque_lines = candidate_lines
        manual_line = non_cheque_lines.filtered(lambda line: line.code == "manual")[:1]
        return manual_line or non_cheque_lines[:1]

    def _ensure_standard_payment_routing_for_cross_settlement(self):
        self.ensure_one()
        if not self._is_cheque_payment_method_line(self.payment_method_line_id):
            return self
        has_cheque_lines = bool(
            getattr(self, "wizard_inbound_cheque_lines", False)
            or getattr(self, "wizard_outbound_cheque_lines", False)
        )
        if has_cheque_lines:
            return self
        fallback_line = self._get_non_cheque_payment_method_line()
        if fallback_line:
            self.write(
                {
                    "journal_id": fallback_line.journal_id.id,
                    "payment_method_line_id": fallback_line.id,
                }
            )
            return self.with_context(
                default_journal_id=fallback_line.journal_id.id,
                default_payment_method_line_id=fallback_line.id,
            )
        return self

    def _prepare_settlement_reference(self, current_moves, cross_lines):
        current_refs = [self._get_document_reference(move) for move in current_moves]
        opposite_refs = [self._get_document_reference(move) for move in cross_lines.move_id]
        ref_chunks = ["PAY-SETTLE"]
        if current_refs:
            ref_chunks.append("CUR: %s" % ", ".join(current_refs[:3]))
            if len(current_refs) > 3:
                ref_chunks[-1] += " (+%s more)" % (len(current_refs) - 3)
        if opposite_refs:
            ref_chunks.append("OFF: %s" % ", ".join(opposite_refs[:3]))
            if len(opposite_refs) > 3:
                ref_chunks[-1] += " (+%s more)" % (len(opposite_refs) - 3)
        narration = "\n".join(
            [
                "Partner Payment Settlement",
                "Partner: %s" % self.partner_id.display_name,
                "Current Documents: %s" % (", ".join(current_refs) or "-"),
                "Offset Documents: %s" % (", ".join(opposite_refs) or "-"),
            ]
        )
        return " | ".join(ref_chunks), narration

    def _build_settlement_move(self, current_allocations, cross_lines):
        self.ensure_one()
        current_moves = self.env["account.move"].browse(
            [allocation["move_id"].id for allocation in current_allocations]
        )
        ref, narration = self._prepare_settlement_reference(current_moves, cross_lines)
        line_commands = []

        for cross_line in cross_lines:
            signed_amount = cross_line.amount_to_settle
            if cross_line.residual_signed_amount < 0:
                signed_amount *= -1
            debit = signed_amount if signed_amount > 0 else 0.0
            credit = -signed_amount if signed_amount < 0 else 0.0
            if cross_line.account_id.account_type == "asset_receivable":
                debit, credit = credit, debit
            line_commands.append(
                Command.create(
                    {
                        "partner_id": self.partner_id.id,
                        "account_id": cross_line.account_id.id,
                        "name": self._get_settlement_line_name(cross_line.move_id),
                        "debit": debit,
                        "credit": credit,
                    }
                )
            )

        for allocation in current_allocations:
            account_type = allocation["account_type"]
            signed_amount = allocation["amount"]
            if account_type == "asset_receivable":
                debit = 0.0
                credit = signed_amount
            else:
                debit = signed_amount
                credit = 0.0
            line_commands.append(
                Command.create(
                    {
                        "partner_id": self.partner_id.id,
                        "account_id": allocation["account_id"].id,
                        "name": self._get_settlement_line_name(allocation["move_id"]),
                        "debit": debit,
                        "credit": credit,
                    }
                )
            )

        move = self.env["account.move"].create(
            {
                "journal_id": self.journal_id.id,
                "date": self.payment_date,
                "ref": ref,
                "narration": narration,
                "company_id": self.company_id.id,
                "line_ids": line_commands,
            }
        )
        return move

    def _create_cross_settlement_move(self):
        self.ensure_one()
        selected_cross_lines = self._validate_cross_settlement_inputs()
        if not selected_cross_lines:
            return self.env["account.move"]

        remaining_to_settle = self.cross_settlement_amount
        current_account_type = self._get_current_account_type()
        current_allocations = []
        current_moves = self.line_ids.move_id.sorted(key=lambda move: (move.invoice_date or fields.Date.today(), move.id))
        for move in current_moves:
            if self.currency_id.compare_amounts(remaining_to_settle, 0.0) <= 0:
                break
            open_lines = self._get_open_move_lines(move, current_account_type)
            if not open_lines:
                continue
            signed_open_amount = self._get_signed_open_amount(open_lines, current_account_type)
            if self.currency_id.compare_amounts(signed_open_amount, 0.0) <= 0:
                continue
            amount = min(signed_open_amount, remaining_to_settle)
            amount = self.currency_id.round(amount)
            current_allocations.append(
                {
                    "move_id": move,
                    "account_id": open_lines[0].account_id,
                    "open_lines": open_lines,
                    "amount": amount,
                    "account_type": current_account_type,
                }
            )
            remaining_to_settle = self.currency_id.round(remaining_to_settle - amount)

        if self.currency_id.compare_amounts(remaining_to_settle, 0.0) > 0:
            raise UserError(
                _("The current payment documents do not have enough remaining open amount to complete the selected settlement.")
            )

        move = self._build_settlement_move(current_allocations, selected_cross_lines)
        move.action_post()

        settlement_lines = move.line_ids.filtered(
            lambda line: line.partner_id == self.partner_id
            and line.account_id.account_type in ("asset_receivable", "liability_payable")
            and not line.reconciled
        )

        for cross_line in selected_cross_lines:
            open_lines = self._get_open_move_lines(cross_line.move_id, cross_line.account_id.account_type)
            settle_line = settlement_lines.filtered(
                lambda line: line.account_id == cross_line.account_id and line.name == self._get_settlement_line_name(cross_line.move_id)
            )[:1]
            (open_lines | settle_line).reconcile()

        for allocation in current_allocations:
            settle_line = settlement_lines.filtered(
                lambda line: line.account_id == allocation["account_id"] and line.name == self._get_settlement_line_name(allocation["move_id"])
            )[:1]
            (allocation["open_lines"] | settle_line).reconcile()

        return move

    def _sync_multi_deduction_balance(self):
        self.ensure_one()
        if not getattr(self, "deduction_ids", False):
            return
        expected = self._get_cross_expected_deduction_amount()
        effective_deductions = self._get_effective_deduction_lines()
        current = sum(effective_deductions.mapped("amount"))
        if self.currency_id.compare_amounts(expected, current) == 0:
            return
        target = (
            effective_deductions.filtered(
                lambda deduction: not deduction.is_open and not self._is_wht_deduction_line(deduction)
            )[-1:]
            or effective_deductions.filtered(lambda deduction: not self._is_wht_deduction_line(deduction))[-1:]
        )
        if target:
            target.update({"amount": target.amount + (expected - current)})

    @api.constrains("deduction_ids", "payment_difference_handling")
    def _check_deduction_amount(self):
        if self.env.context.get("skip_wht_deduct") or self.env.context.get("in_wht_sync"):
            return
        for wizard in self:
            if wizard.cross_settlement_line_ids.filtered("is_selected"):
                continue
            if wizard.payment_difference_handling != "reconcile_multi_deduct":
                continue
            wizard._validate_effective_deduction_balance()

    def action_create_payments(self):
        self.ensure_one()
        self._cleanup_cross_settlement_auto_deductions()
        self._compute_payment_difference()
        self._validate_effective_deduction_balance()
        selected_cross_lines = self._validate_cross_settlement_inputs()
        if not selected_cross_lines:
            return super().action_create_payments()

        if self.currency_id.compare_amounts(self.amount, 0.0) < 0:
            raise UserError(_("Cross settlement amount cannot exceed the payment document open amount."))

        result = True
        if self.currency_id.compare_amounts(self.amount, 0.0) > 0:
            payment_wizard = self._ensure_standard_payment_routing_for_cross_settlement()
            result = super(AccountPaymentRegister, payment_wizard).action_create_payments()

        payments = self._get_created_payment_records(result)
        if payments:
            self = self.with_context(payment_id=payments[0].id)
        else:
            self = self.with_context(net_invoice_refund=1)

        settlement_move = self._create_cross_settlement_move()
        if result is True:
            return {
                "type": "ir.actions.act_window",
                "name": _("Settlement Journal Entry"),
                "res_model": "account.move",
                "view_mode": "form",
                "res_id": settlement_move.id,
            }
        return result


class AccountPaymentRegisterCrossSettlementLine(models.TransientModel):
    _name = "account.payment.register.cross.settlement.line"
    _description = "Account Payment Register Cross Settlement Line"
    _order = "move_date, id"

    wizard_id = fields.Many2one("account.payment.register", required=True, ondelete="cascade")
    move_id = fields.Many2one("account.move", required=True, readonly=True)
    move_type = fields.Selection(related="move_id.move_type", string="Move Type", readonly=True)
    document_label = fields.Char(
        string="Document Type",
        compute="_compute_document_label",
    )
    move_date = fields.Date(related="move_id.invoice_date", string="Document Date", readonly=True)
    currency_id = fields.Many2one("res.currency", required=True, readonly=True)
    account_id = fields.Many2one("account.account", required=True, readonly=True)
    residual_signed_amount = fields.Monetary(
        string="Open Amount",
        currency_field="currency_id",
        readonly=True,
    )
    amount_to_settle = fields.Monetary(
        string="Settle Amount",
        currency_field="currency_id",
    )
    is_selected = fields.Boolean(string="Select")

    @api.depends("move_id.move_type", "move_id.debit_origin_id")
    def _compute_document_label(self):
        for line in self:
            if not line.move_id:
                line.document_label = False
                continue
            wizard = line.wizard_id
            if wizard:
                line.document_label = wizard._get_document_label(line.move_id)
                continue
            if line.move_id.move_type in ("out_refund", "in_refund"):
                line.document_label = "CN"
            elif line.move_id.debit_origin_id:
                line.document_label = "DN"
            elif line.move_id.move_type == "out_invoice":
                line.document_label = "Invoice"
            elif line.move_id.move_type == "in_invoice":
                line.document_label = "Bill"
            else:
                line.document_label = line.move_id.move_type or "Document"
