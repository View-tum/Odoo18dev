from odoo import api, fields, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    company_group_id = fields.Many2one(
        "res.partner",
        string="Company Group",
        domain="[('is_company_group', '=', True)]",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if not self.env.context.get("is_group_payment"):
            return res

        allocation_commands = res.get("allocation_line_ids")
        amount_map = self.env.context.get("group_payment_amounts_by_move_id") or {}
        if not allocation_commands or not amount_map:
            return res

        normalized_amount_map = {}
        for move_id, amount in amount_map.items():
            try:
                normalized_amount_map[int(move_id)] = abs(amount or 0.0)
            except (TypeError, ValueError):
                continue
        if not normalized_amount_map:
            return res

        prepared_commands = []
        move_line_ids = []
        for command in allocation_commands:
            if not isinstance(command, (list, tuple)) or len(command) < 3 or command[0] != 0:
                prepared_commands.append(command)
                continue
            vals = dict(command[2] or {})
            prepared_commands.append((command[0], command[1], vals))
            if vals.get("move_line_id"):
                move_line_ids.append(vals["move_line_id"])

        if not move_line_ids:
            return res

        move_line_map = {
            line.id: line for line in self.env["account.move.line"].browse(move_line_ids).exists()
        }
        if not move_line_map:
            return res

        updated_commands = []
        for command in prepared_commands:
            if not isinstance(command, (list, tuple)) or len(command) < 3 or command[0] != 0:
                updated_commands.append(command)
                continue

            vals = dict(command[2] or {})
            move_line = move_line_map.get(vals.get("move_line_id"))
            if not move_line:
                updated_commands.append(command)
                continue

            move_id = move_line.move_id.id
            if move_id not in normalized_amount_map:
                updated_commands.append(command)
                continue

            default_amount = vals.get("amount_to_pay", 0.0) or 0.0
            default_abs = abs(default_amount)
            remaining_abs = normalized_amount_map[move_id]
            alloc_abs = min(default_abs, remaining_abs)
            sign = -1 if default_amount < 0 else 1

            vals["amount_to_pay"] = sign * alloc_abs
            vals["amount_residual"] = default_amount - vals["amount_to_pay"]
            normalized_amount_map[move_id] = max(0.0, remaining_abs - alloc_abs)

            updated_commands.append((command[0], command[1], vals))

        res["allocation_line_ids"] = updated_commands
        return res

    @api.model
    def _get_line_batch_key(self, line):
        batch_key = super()._get_line_batch_key(line)
        if not self.env.context.get("is_group_payment"):
            return batch_key

        # Avoid splitting by invoice partner bank account in group collection flow.
        batch_key["partner_bank_id"] = False

        # Group all selected invoices into 1 batch so Odoo enables can_edit_wizard and shows the multi-deduction tab
        first_line_id = self.env.context.get('active_ids', [line.move_id.id])[0]
        first_line = self.env['account.move'].browse(first_line_id).line_ids.filtered(lambda l: l.account_type in ('asset_receivable', 'liability_payable'))
        if first_line:
            first_line = first_line[0]
            batch_key["partner_id"] = first_line.partner_id.id
            batch_key["account_id"] = first_line.account_id.id
            batch_key["currency_id"] = first_line.currency_id.id
            batch_key["partner_type"] = 'customer' if first_line.account_type == 'asset_receivable' else 'supplier'

        return batch_key

    @api.depends("can_edit_wizard")
    def _compute_group_payment(self):
        super()._compute_group_payment()
        for wizard in self:
            if wizard._context.get("is_group_payment"):
                wizard.group_payment = True

    def _create_payment_vals_from_wizard(self, batch_result):
        vals = super()._create_payment_vals_from_wizard(batch_result)
        if self.company_group_id:
            vals["company_group_id"] = self.company_group_id.id
        if self.communication:
            vals["group_payment_memo"] = self.communication
        return vals

    def _create_payment_vals_from_batch(self, batch_result):
        vals = super()._create_payment_vals_from_batch(batch_result)
        if self.company_group_id:
            vals["company_group_id"] = self.company_group_id.id
        return vals

    def _create_payments(self):
        if not self._context.get("is_group_payment"):
            payments = super()._create_payments()
            group_payment_id = self._context.get("default_group_payment_id")
            if group_payment_id:
                group_payment = self.env["account.customer.group.payment"].browse(group_payment_id)
                if group_payment.exists():
                    group_payment.write({
                        "generated_payment_ids": [(4, p.id) for p in payments],
                        "state": "done",
                    })
            return payments

        # Option A: Create 1 payment per partner, but apply all differences/deductions to the LAST payment generated.
        self.ensure_one()
        all_lines = self.line_ids.move_id.line_ids.filtered(lambda l: l.account_type in ('asset_receivable', 'liability_payable') and not l.reconciled)

        # Group lines by the actual partner
        partner_lines_map = {}
        for line in all_lines:
            partner = line.partner_id
            if partner not in partner_lines_map:
                partner_lines_map[partner] = self.env['account.move.line']
            partner_lines_map[partner] |= line

        payments = self.env['account.payment']
        to_process = []
        partners = list(partner_lines_map.keys())

        total_source_ar = sum(abs(sum(lines.mapped('amount_residual'))) for lines in partner_lines_map.values())
        allocated_amount_so_far = 0.0

        full_batch_result = self.batches[0] if self.batches else None
        has_wizard_deductions = not self.currency_id.is_zero(self.payment_difference) and self.payment_difference_handling in ('reconcile', 'reconcile_multi_deduct')
        full_wizard_vals = self._create_payment_vals_from_wizard(full_batch_result) if full_batch_result and has_wizard_deductions else {}
        
        # We need to keep track of how much of each write-off line has been allocated
        # to avoid rounding losses.
        write_off_allocation = []
        if full_wizard_vals.get('write_off_line_vals'):
            for wo_line in full_wizard_vals.get('write_off_line_vals', []):
                write_off_allocation.append({
                    'original': wo_line,
                    'allocated_amount_currency': 0.0,
                    'allocated_balance': 0.0,
                })

        for i, partner in enumerate(partners):
            lines = partner_lines_map[partner]
            is_last = (i == len(partners) - 1)
            partner_ar = abs(sum(lines.mapped('amount_residual')))

            batch_result = {
                'lines': lines,
                'payment_values': {
                    'currency_id': lines[0].currency_id.id,
                    'partner_bank_id': False,
                    'payment_type': 'inbound' if lines[0].balance > 0 else 'outbound',
                    'partner_type': 'customer' if lines[0].account_type == 'asset_receivable' else 'supplier',
                    'partner_id': partner.id,
                    'source_amount_currency': partner_ar,
                    'source_currency_id': lines[0].currency_id.id,
                }
            }

            payment_vals = self._create_payment_vals_from_batch(batch_result)
            ratio = (partner_ar / total_source_ar) if total_source_ar else 0.0

            if has_wizard_deductions:
                if is_last:
                    partner_net_amount = self.amount - allocated_amount_so_far
                else:
                    partner_net_amount = self.currency_id.round(self.amount * ratio)
                    allocated_amount_so_far += partner_net_amount
                
                payment_vals['amount'] = partner_net_amount
                payment_vals['partner_id'] = partner.id

                # Distribute write-off lines
                if write_off_allocation:
                    payment_vals['write_off_line_vals'] = []
                    for wo_state in write_off_allocation:
                        wo = wo_state['original']
                        if is_last:
                            wo_amount_curr = wo['amount_currency'] - wo_state['allocated_amount_currency']
                            wo_bal = wo['balance'] - wo_state['allocated_balance']
                        else:
                            wo_amount_curr = self.currency_id.round(wo['amount_currency'] * ratio)
                            wo_bal = self.company_id.currency_id.round(wo['balance'] * ratio)
                            wo_state['allocated_amount_currency'] += wo_amount_curr
                            wo_state['allocated_balance'] += wo_bal

                        # Only append if non-zero
                        if not self.currency_id.is_zero(wo_amount_curr) or not self.company_id.currency_id.is_zero(wo_bal):
                            payment_vals['write_off_line_vals'].append({
                                'name': wo['name'],
                                'account_id': wo['account_id'],
                                'partner_id': partner.id,
                                'currency_id': wo['currency_id'],
                                'amount_currency': wo_amount_curr,
                                'balance': wo_bal,
                            })
            else:
                if is_last:
                    payment_vals['amount'] = self.amount - allocated_amount_so_far
                else:
                    payment_vals['amount'] = partner_ar
                    allocated_amount_so_far += partner_ar
                payment_vals['partner_id'] = partner.id

            to_process.append({
                'create_vals': payment_vals,
                'to_reconcile': lines,
                'batch': batch_result,
            })

        # Process standard creation steps
        payments = self._init_payments(to_process, edit_mode=True)
        self._post_payments(to_process, edit_mode=True)
        self._reconcile_payments(to_process, edit_mode=True)

        group_payment_id = self._context.get("default_group_payment_id")
        if group_payment_id:
            group_payment = self.env["account.customer.group.payment"].browse(group_payment_id)
            if group_payment.exists():
                group_payment.write({
                    "generated_payment_ids": [(4, p.id) for p in payments],
                    "state": "done",
                })
        return payments

    def _reconcile_payments(self, to_process, edit_mode=False):
        if not self._context.get("is_group_payment"):
            return super()._reconcile_payments(to_process, edit_mode=edit_mode)

        domain = [
            ('parent_state', '=', 'posted'),
            ('account_type', 'in', self.env['account.payment']._get_valid_payment_account_types()),
            ('reconciled', '=', False),
        ]
        for vals in to_process:
            payment = vals['payment']
            payment_lines = payment.move_id.line_ids.filtered_domain(domain)
            lines = vals['to_reconcile']

            for account in payment_lines.account_id:
                to_reconcile_lines = (payment_lines + lines)\
                    .filtered_domain([
                        ('account_id', '=', account.id),
                        ('reconciled', '=', False),
                        ('parent_state', '=', 'posted'),
                    ])
                if len(to_reconcile_lines) >= 2:
                    to_reconcile_lines.reconcile()
            lines.move_id.matched_payment_ids += payment

    def check_customers(self):
        if self._context.get("is_group_payment"):
            return True
        return super(AccountPaymentRegister, self).check_customers()

