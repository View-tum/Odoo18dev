from markupsafe import Markup
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ChequeInboundOutbound(models.Model):
    _name = 'cheque.inbound.outbound'
    _description = 'Cheque'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Cheque No.', copy=False, default='New', tracking=True)
    cheque_type = fields.Selection([('inbound', 'Inbound'),
                                    ('outbound', 'Outbound')], default='inbound', string='Type', tracking=True)
    bank_account_journal_id = fields.Many2one('account.journal', 'Bank Account', domain=[('type', '=', 'bank')], copy=False, tracking=True)
    pay_partner_id = fields.Many2one('res.partner', 'Partner', tracking=True)
    payee_name_id = fields.Many2one(
        'res.partner.payee.name',
        string='Payee Name',
        domain="[('partner_id', '=', pay_partner_id)]",
        compute='_compute_payee_name_id',
        store=True,
        readonly=False,
    )
    partner_name = fields.Char(
        'Payee Name Text',
        compute='_compute_partner_name',
        store=True,
    )
    amount = fields.Monetary('Amount', tracking=True)
    payment_method_line_id = fields.Many2one('account.payment.method.line', 'Payment Method')
    payment_method_line_account_id = fields.Many2one('account.account', 'Payment Method Account')
    filtered_payment_method_line_ids = fields.Many2many(
        'account.payment.method.line',
        compute='_compute_filtered_payment_method_line_ids',
        string='Payment Methods',
        store=True
    )
    ac_payee = fields.Boolean('A/C Payee')
    memo = fields.Char('Memo')
    date = fields.Date('Payment Date', tracking=True)
    cheque_date = fields.Date('Cheque Date', default=fields.Date.context_today, tracking=True)
    cheque_received_date = fields.Date('Cheque Received Date', tracking=True)
    clearing_date = fields.Date('Clearing Date', tracking=True)
    cheque_optinal = fields.Selection([('return', 'Void'),
                                    ('transform', 'Transform')], string='Cheque Optional', tracking=True)
    return_date = fields.Date('Void Date', tracking=True)
    transform_date = fields.Date('Transform Date', tracking=True)
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        help='Utility field to express amount currency',
        default=lambda self: self.env.company.currency_id,
        readonly=True,
    )
    amount_total_words = fields.Char(string="Amount total in words", compute="_compute_amount_total_words")
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    is_reverse_cheque_entry = fields.Boolean('Is Reverse Cheque Entry?', related='company_id.is_reverse_cheque_entry', store=True)
    state = fields.Selection([('draft', 'Draft'),
                              ('waiting_confirm', 'Waiting Confirm'),
                              ('confirmed', 'Confirmed'),
                              ('bank_deposit', 'Bank Deposit'),
                              ('return', 'Void'),
                              ('paid', 'Paid'),
                              ('transform', 'Transform'),
                              ('cancelled', 'Cancelled')], default='draft', string='Status', tracking=True)
    payment_id = fields.Many2one('account.payment', 'Payment')
    payment_ids = fields.Many2many('account.payment', string='Payments')
    count_payment = fields.Integer(compute='_count_payment', string='Payments')
    count_move = fields.Integer(compute='_count_move', string='Journals')
    cheque_validation_entry_id = fields.Many2one('account.move', 'Cheque Validation Entry')
    count_void_move = fields.Integer(compute='_count_void_move', string='Void Entries')
    count_transform_move = fields.Integer(compute='_count_transform_move', string='Transform Entries')
    reconcile_move_ids = fields.Many2many(
        'account.move',
        compute='_compute_reconcile_moves',
        string='Reconcile Entries',
    )
    count_reconcile_move = fields.Integer(
        compute='_compute_reconcile_moves',
        string='Reconcile Entries',
    )
    payment_move_ids = fields.Many2many(
        'account.move',
        compute='_compute_payment_moves',
        string='Payment Entries',
    )
    count_payment_move = fields.Integer(
        compute='_compute_payment_moves',
        string='Payment Entries',
    )
    cancel_deposit_move_ids = fields.Many2many(
        'account.move',
        'cheque_cancel_deposit_move_rel',
        'cheque_id',
        'move_id',
        string='Cancel Deposit Entries',
        copy=False,
    )
    cancel_payment_move_ids = fields.Many2many(
        'account.move',
        'cheque_cancel_payment_move_rel',
        'cheque_id',
        'move_id',
        string='Cancel Payment Entries',
        copy=False,
    )
    count_cancel_deposit_move = fields.Integer(
        compute='_count_cancel_deposit_move',
        string='Cancel Deposit Entries',
    )
    count_cancel_payment_move = fields.Integer(
        compute='_count_cancel_payment_move',
        string='Cancel Payment Entries',
    )
    reversed_move_ids = fields.Many2many(
        'account.move',
        compute='_compute_reversed_moves',
        string='Reversed Entries',
    )
    count_reversed_move = fields.Integer(
        compute='_compute_reversed_moves',
        string='Reversed Entries',
    )

    # Payment Detail
    cheque_payment_detail_lines = fields.One2many('cheque.payment.detail.lines', 'cheque_inbound_outbound_id', 'Payment Detail Lines')

    # Transform Detail
    transform_detail_lines = fields.One2many('cheque.transform.detail.lines', 'cheque_inbound_outbound_id', 'Transform Detail Lines')
    cheque_amount = fields.Monetary('Cheque Amount')
    change_amount = fields.Monetary('Change Amount', compute='_compute_change_amount', store=True)
    balance = fields.Monetary('Balance', compute='_compute_balance', store=True)
    cheque_transform_cheque_ids = fields.Many2many('cheque.inbound.outbound', 'transform_cheque', 'trasform_id', 'cheque_id', string='Cheque Paying/Receiving', copy=False)
    count_transform_cheque = fields.Integer(compute='_count_transform_cheque', string="Tranform")
    original_cheque_transform_id = fields.Many2one('cheque.inbound.outbound', 'Original Cheque')
    count_original_cheque = fields.Integer(compute='_count_original_cheque', string='Original Cheque Count')
    count_payment_outstanding = fields.Integer(compute='_count_payment_outstanding', string='Outstanding')

    # Outbound
    cheque_id = fields.Many2one('cheque.book.lines', 'Cheque No.', readonly=True, copy=False, tracking=True)
    cheque_book_id = fields.Many2one('cheque.book', string="Cheque Book", readonly=True)

    # Inbound
    payment_ref = fields.Char('Payment Reference')
    cheque_bank_id = fields.Many2one('res.bank', string="Cheque Bank")
    cheque_bank_branch = fields.Char(string="Cheque Bank Branch")

    # Other Info
    cheque_journal_entry_id = fields.Many2one('account.move', 'Cheque Journal')
    cheque_transfrom_journal_entry_id = fields.Many2one('account.move', 'Transform Journal')
    cheque_return_journal_move_id = fields.Many2one('account.move', 'Void Journal')

    # Description
    description = fields.Html('Description')

    # Dynamic Cheque
    dynamic_cheque_list = fields.Many2many('dynamic.cheque', compute='_compute_dynamic_cheque_list')
    dynamic_io_cheque_id = fields.Many2one('dynamic.cheque', string="Cheque Form", tracking=True, domain="[('id', 'in', dynamic_cheque_list)]")
    is_cheque_print = fields.Boolean('Is Cheque Print?')
    void_reason = fields.Char("Void Reason")

    @api.onchange('cheque_id')
    def onchange_cheque_id(self):
        if self.cheque_id and self.cheque_type == 'inbound':
            self.name = self.cheque_id.name

    @api.onchange('cheque_date')
    def _onchange_cheque_date_sync(self):
        if self.cheque_type == 'inbound' and self.cheque_date:
            self.date = self.cheque_date

    @api.onchange('date')
    def _onchange_date_sync(self):
        if self.cheque_type == 'inbound' and self.date:
            self.cheque_date = self.date

    @api.depends('payee_name_id', 'payee_name_id.name')
    def _compute_partner_name(self):
        for rec in self:
            rec.partner_name = rec.payee_name_id.name if rec.payee_name_id else ''

    @api.depends('pay_partner_id')
    def _compute_payee_name_id(self):
        PayeeName = self.env['res.partner.payee.name']
        for rec in self:
            if rec.pay_partner_id:
                existing = PayeeName.search([
                    ('partner_id', '=', rec.pay_partner_id.id),
                    ('name', '=', rec.pay_partner_id.name),
                ], limit=1)
                if existing and not existing.is_default:
                    existing.sudo().write({'is_default': True})
                if not existing:
                    existing = PayeeName.sudo().create({
                        'partner_id': rec.pay_partner_id.id,
                        'name': rec.pay_partner_id.name,
                        'is_default': True,
                    })
                rec.payee_name_id = existing.id
            else:
                rec.payee_name_id = False

    @api.onchange('cheque_optinal')
    def _onchange_cheque_optinal(self):
        if self.cheque_optinal == 'transform' and self.state != 'return':
            self.cheque_optinal = False
            self.transform_date = False
            return {
                'warning': {
                    'title': _('Transform not allowed'),
                    'message': _('You can only transform a cheque in Void state.'),
                }
            }

    @api.depends('amount', 'currency_id')
    def _compute_amount_total_words(self):
        for cheque in self:
            cheque.amount_total_words = cheque.currency_id.amount_to_text(cheque.amount).replace(',', '')

    def _compute_dynamic_cheque_list(self):
        for cheque in self:
            cheque.dynamic_cheque_list = cheque.bank_account_journal_id.dynamic_cheque_id.ids
            if cheque.bank_account_journal_id.dynamic_cheque_id and not cheque.dynamic_io_cheque_id:
                cheque.dynamic_io_cheque_id = cheque.bank_account_journal_id.dynamic_cheque_id.ids[0]

    @api.onchange('bank_account_journal_id')
    def onchange_bank_account_journal_id(self):
        return {'domain': {'dynamic_io_cheque_id': [('id', 'in', self.bank_account_journal_id.dynamic_cheque_id.ids)]}}

    @api.depends('bank_account_journal_id')
    def _compute_filtered_payment_method_line_ids(self):
        for rec in self:
            if rec.cheque_type == 'inbound':
                inbound_payment_method_line = self.env['account.payment.method.line'].search([('journal_id', '=', rec.bank_account_journal_id.id), ('payment_type', '=', 'outbound')])
                rec.filtered_payment_method_line_ids = [(6, 0 , inbound_payment_method_line.ids)]
            if rec.cheque_type == 'outbound':
                outbound_payment_method_line = self.env['account.payment.method.line'].search([('journal_id', '=', rec.bank_account_journal_id.id), ('payment_type', '=', 'inbound')])
                rec.filtered_payment_method_line_ids = [(6, 0 , outbound_payment_method_line.ids)]

    def _count_payment(self):
        for cheque in self:
            cheque.count_payment = len(cheque.payment_ids | cheque.payment_id)

    def action_view_payment_cheque(self):
        return self._get_action_view_payment_cheque(self.payment_ids | self.payment_id)

    def action_view_reconcile_entries(self):
        self.ensure_one()
        moves = self.reconcile_move_ids
        action = self.env['ir.actions.actions']._for_xml_id('account.action_move_journal_line')
        action['domain'] = [('id', 'in', moves.ids)]
        action['context'] = dict(self.env.context, create=0, edit=0)
        if len(moves) == 1:
            form_view = [(self.env.ref('account.view_move_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [
                    (state, view) for state, view in action['views'] if view != 'form'
                ]
            else:
                action['views'] = form_view
            action['res_id'] = moves.id
        return action

    def action_view_payment_entries(self):
        self.ensure_one()
        moves = self.payment_move_ids
        action = self.env['ir.actions.actions']._for_xml_id('account.action_move_journal_line')
        action['domain'] = [('id', 'in', moves.ids)]
        action['context'] = dict(self.env.context, create=0, edit=0)
        if len(moves) == 1:
            form_view = [(self.env.ref('account.view_move_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [
                    (state, view) for state, view in action['views'] if view != 'form'
                ]
            else:
                action['views'] = form_view
            action['res_id'] = moves.id
        return action

    def _get_action_view_payment_cheque(self, cheque):
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_account_payments")

        if len(cheque) > 1:
            action['domain'] = [('id', 'in', cheque.ids)]
        elif cheque:
            form_view = [(self.env.ref('account.view_account_payment_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = cheque.id
        return action

    def _count_payment_outstanding(self):
        for cheque in self:
            cheque.count_payment_outstanding = self.env['account.payment'].search_count([('cheque_id', '=', cheque.id)])

    def _count_move(self):
        for cheque in self:
            cheque.count_move = len(cheque.cheque_journal_entry_id)

    @api.depends(
        'cheque_journal_entry_id',
        'cheque_journal_entry_id.line_ids.matched_debit_ids',
        'cheque_journal_entry_id.line_ids.matched_credit_ids',
    )
    def _compute_reconcile_moves(self):
        for cheque in self:
            moves = self.env['account.move']
            deposit_move = cheque.cheque_journal_entry_id
            if deposit_move:
                lines = deposit_move.line_ids.filtered(lambda l: l.account_id.reconcile)
                partials = lines.matched_debit_ids | lines.matched_credit_ids
                counterpart_lines = (partials.debit_move_id + partials.credit_move_id) - lines
                moves = counterpart_lines.mapped('move_id').filtered(lambda m: m.statement_line_id)
            cheque.reconcile_move_ids = moves
            cheque.count_reconcile_move = len(moves)

    def _get_all_payment_entry_moves(self):
        """Return all journal entries related to this cheque across all cycles.

        This intentionally includes current-cycle entries + historical reversals so
        the "Payment Entry" smart button can be used as a full audit trail.
        """
        self.ensure_one()
        moves = self.env['account.move']

        # Current linked payment/accounting entries
        moves |= (self.payment_ids | self.payment_id).mapped('move_id')
        moves |= self.cheque_validation_entry_id | self.cheque_journal_entry_id
        moves |= self.cheque_return_journal_move_id | self.cheque_transfrom_journal_entry_id

        # Explicitly tracked cancel/reversal history
        moves |= self.cancel_deposit_move_ids | self.cancel_payment_move_ids
        moves |= self._get_all_reversed_moves()

        # Fallback: any move tagged to this cheque (covers manual/legacy flows)
        moves |= self.env['account.move'].search([
            ('cheque_inbound_outbound_id', '=', self.id),
        ])

        return moves

    @api.depends(
        'payment_ids.move_id',
        'payment_id.move_id',
        'cheque_validation_entry_id',
        'cheque_journal_entry_id',
        'cheque_return_journal_move_id',
        'cheque_transfrom_journal_entry_id',
        'cancel_deposit_move_ids',
        'cancel_payment_move_ids',
        'cancel_deposit_move_ids.reversed_entry_id',
        'cancel_payment_move_ids.reversed_entry_id',
        'payment_ids.move_id.reversed_entry_id',
        'payment_id.move_id.reversed_entry_id',
    )
    def _compute_payment_moves(self):
        for cheque in self:
            moves = cheque._get_all_payment_entry_moves()
            cheque.payment_move_ids = moves
            cheque.count_payment_move = len(moves)

    @api.depends('cheque_return_journal_move_id')
    def _count_void_move(self):
        move_map = self._get_status_move_map('void')
        for cheque in self:
            moves = move_map.get(cheque.id, self.env['account.move'])
            if cheque.cheque_return_journal_move_id and cheque.cheque_return_journal_move_id.status != 'cancel':
                moves |= cheque.cheque_return_journal_move_id
            cheque.count_void_move = len(moves)

    @api.depends('cancel_deposit_move_ids', 'cheque_validation_entry_id', 'cheque_journal_entry_id')
    def _count_cancel_deposit_move(self):
        for cheque in self:
            moves = cheque._get_latest_reversal_moves(cheque.cheque_validation_entry_id | cheque.cheque_journal_entry_id)
            moves |= cheque.cancel_deposit_move_ids.filtered(
                lambda m: (not m.cheque_inbound_outbound_id or m.cheque_inbound_outbound_id == cheque)
            )
            cheque.count_cancel_deposit_move = len(moves)

    @api.depends('cancel_payment_move_ids', 'payment_ids.move_id', 'payment_id.move_id')
    def _count_cancel_payment_move(self):
        for cheque in self:
            payment_moves = (cheque.payment_ids | cheque.payment_id).mapped('move_id')
            moves = cheque._get_latest_reversal_moves(payment_moves)
            moves |= cheque.cancel_payment_move_ids.filtered(
                lambda m: (not m.cheque_inbound_outbound_id or m.cheque_inbound_outbound_id == cheque)
            )
            cheque.count_cancel_payment_move = len(moves)

    @api.depends(
        'cancel_deposit_move_ids',
        'cancel_payment_move_ids',
        'cheque_validation_entry_id',
        'cheque_journal_entry_id',
        'payment_ids.move_id',
        'payment_id.move_id',
    )
    def _compute_reversed_moves(self):
        for cheque in self:
            moves = cheque._get_all_reversed_moves()
            cheque.reversed_move_ids = moves
            cheque.count_reversed_move = len(moves)

    @api.depends('cheque_transfrom_journal_entry_id')
    def _count_transform_move(self):
        move_map = self._get_status_move_map('transform')
        for cheque in self:
            moves = move_map.get(cheque.id, self.env['account.move'])
            if cheque.cheque_transfrom_journal_entry_id:
                moves |= cheque.cheque_transfrom_journal_entry_id
            cheque.count_transform_move = len(moves)

    def get_partner_account(self):
        if self.cheque_type == 'inbound':
            account = self.pay_partner_id.property_account_receivable_id
        else:
            account = self.pay_partner_id.property_account_payable_id
        if not account:
            raise UserError(_("Partner is missing a valid receivable or payable account."))
        return account.id

    def _get_status_move_map(self, status):
        moves = self.env['account.move'].search([
            ('cheque_inbound_outbound_id', 'in', self.ids),
            ('status', '=', status),
        ])
        move_map = {cheque.id: self.env['account.move'] for cheque in self}
        for move in moves:
            move_map[move.cheque_inbound_outbound_id.id] |= move
        return move_map

    def _get_latest_reversal_moves(self, source_moves):
        self.ensure_one()
        if not source_moves:
            return self.env['account.move']

        reversals = self.env['account.move'].search([
            ('reversed_entry_id', 'in', source_moves.ids),
            ('state', 'in', ['draft', 'posted']),
        ], order='id desc')

        latest_ids = []
        seen_source_ids = set()
        for move in reversals:
            source_id = move.reversed_entry_id.id
            if source_id and source_id not in seen_source_ids:
                seen_source_ids.add(source_id)
                latest_ids.append(move.id)
        return self.env['account.move'].browse(latest_ids)

    def _get_all_reversed_moves(self):
        self.ensure_one()
        moves = self.env['account.move']
        moves |= self._get_latest_reversal_moves(self.cheque_validation_entry_id | self.cheque_journal_entry_id)
        payment_moves = (self.payment_ids | self.payment_id).mapped('move_id')
        moves |= self._get_latest_reversal_moves(payment_moves)
        moves |= self.cancel_deposit_move_ids.filtered(
            lambda m: (not m.cheque_inbound_outbound_id or m.cheque_inbound_outbound_id == self)
        )
        moves |= self.cancel_payment_move_ids.filtered(
            lambda m: (not m.cheque_inbound_outbound_id or m.cheque_inbound_outbound_id == self)
        )
        return moves

    def _get_bank_and_outstanding_accounts(self):
        self.ensure_one()
        journal = self.bank_account_journal_id
        bank_account = journal.default_account_id
        if not bank_account:
            inbound_lines = journal.inbound_payment_method_line_ids
            outbound_lines = journal.outbound_payment_method_line_ids
            # Mapping in this module: outbound cheque = receiving, inbound cheque = paying.
            if self.cheque_type == 'outbound':
                bank_account = inbound_lines.filtered(lambda l: l.payment_account_id)[:1].payment_account_id
            else:
                bank_account = outbound_lines.filtered(lambda l: l.payment_account_id)[:1].payment_account_id

        outstanding_account = self.payment_method_line_account_id
        if not outstanding_account:
            outstanding_account = (
                journal.inbound_payment_method_line_ids.filtered(lambda l: l.payment_method_id.code == 'cheque')[:1].payment_account_id
                if self.cheque_type == 'outbound'
                else journal.outbound_payment_method_line_ids.filtered(lambda l: l.payment_method_id.code == 'cheque')[:1].payment_account_id
            )
        return bank_account, outstanding_account

    def _ensure_bank_deposit_entry(self):
        self.ensure_one()
        linked_moves = (self.cheque_journal_entry_id | self.cheque_validation_entry_id).filtered(lambda m: m.state == 'posted')
        active_moves = self.env['account.move']
        for move in linked_moves:
            # After Void + Reset to Draft, posted source entries remain for audit but have posted reversals.
            # Those historical entries must not block a new bank-deposit cycle.
            if self.env['account.move'].search_count([
                ('reversed_entry_id', '=', move.id),
                ('state', '=', 'posted'),
            ]):
                continue
            active_moves |= move
        existing_move = active_moves[:1]
        if existing_move:
            if not self.cheque_journal_entry_id:
                self.cheque_journal_entry_id = existing_move.id
            if not self.cheque_validation_entry_id:
                self.cheque_validation_entry_id = existing_move.id
            return existing_move

        bank_account, outstanding_account = self._get_bank_and_outstanding_accounts()
        if not bank_account or not outstanding_account:
            raise UserError(_('Please configure Bank Account and Cheque Outstanding account before bank deposit.'))

        ref = _('Bank Clearing for Cheque %s') % (self.name or '')
        move_vals = {
            'date': self.clearing_date or fields.Date.context_today(self),
            'journal_id': self.bank_account_journal_id.id,
            'ref': ref,
            'line_ids': [
                (0, 0, {
                    'name': ref,
                    'account_id': bank_account.id if self.cheque_type == 'outbound' else outstanding_account.id,
                    'partner_id': self.pay_partner_id.id,
                    'debit': self.amount,
                    'credit': 0.0,
                }),
                (0, 0, {
                    'name': ref,
                    'account_id': outstanding_account.id if self.cheque_type == 'outbound' else bank_account.id,
                    'partner_id': self.pay_partner_id.id,
                    'debit': 0.0,
                    'credit': self.amount,
                }),
            ],
            'cheque_inbound_outbound_id': self.id,
        }
        move = self.env['account.move'].create(move_vals)
        move.action_post()
        self.cheque_journal_entry_id = move.id
        self.cheque_validation_entry_id = move.id
        return move

    def _count_original_cheque(self):
        for cheque in self:
            cheque.count_original_cheque = self.env['cheque.inbound.outbound'].search_count([('id', '=', self.original_cheque_transform_id.id)])

    @api.depends('amount', 'transform_detail_lines')
    def _compute_change_amount(self):
        for record in self:
            change_amount = 0.0
            for line in record.transform_detail_lines:
                change_amount += line.amount
            record.change_amount = change_amount
            record.cheque_amount = record.amount

    @api.depends('cheque_amount', 'change_amount', 'transform_detail_lines')
    def _compute_balance(self):
        for record in self:
            record.balance = record.cheque_amount - record.change_amount

    def action_waiting_confirm(self):
        cheque_book_lines_id = self.env['cheque.book.lines'].search([('name', '=', self.cheque_id.name)])
        if cheque_book_lines_id:
            cheque_book_lines_id.date = self.cheque_date
            cheque_book_lines_id.pay_to = self.pay_partner_id.id
            cheque_book_lines_id.amount = self.amount
            cheque_book_lines_id.memo = self.memo
            cheque_book_lines_id.status = 'waiting_confirm'
        self.state = 'waiting_confirm'

    def action_arrive_confirm(self):
        """Arrival shortcut: move directly to Confirmed."""
        for cheque in self:
            if cheque.state == 'draft':
                cheque.action_waiting_confirm()
            if cheque.state == 'waiting_confirm':
                cheque.action_confirm_pay()

    def action_confirm_pay(self):
        # if not self.clearing_date and not self.cheque_optinal in ['return', 'transform']:
        #     raise UserError(_('Please Add Clearing date. It must be required.'))
        cheque_book_lines_id = self.env['cheque.book.lines'].search([('name', '=', self.cheque_id.name)])
        self.state = 'confirmed'
        self.cheque_id.status = 'confirmed'
        # Keep invoice/bill linked in payment flow:
        # post cheque payments at Confirmed so they reconcile with source invoices/bills.
        payments = (self.payment_ids | self.payment_id).filtered(
            lambda p: p.move_id and p.move_id.state == 'draft'
        )
        if payments:
            payments.with_context(force_post_cheque=True).action_post()
        self._auto_reconcile_linked_payments()

    def _get_candidate_invoice_moves(self, payment):
        self.ensure_one()
        refs = {
            (payment.memo or "").strip(),
            (payment.payment_reference or "").strip(),
            (self.payment_ref or "").strip(),
            (self.memo or "").strip(),
        }
        refs = {ref for ref in refs if ref}
        moves = self.env["account.move"]
        if refs:
            moves |= self.env["account.move"].search([
                ("state", "=", "posted"),
                ("move_type", "in", ("out_invoice", "in_invoice", "out_refund", "in_refund")),
                "|",
                ("name", "in", list(refs)),
                ("ref", "in", list(refs)),
            ])
        if not moves:
            moves = self.env["account.move"].search([
                ("state", "=", "posted"),
                ("partner_id", "=", payment.partner_id.id),
                ("move_type", "in", ("out_invoice", "in_invoice", "out_refund", "in_refund")),
                ("payment_state", "in", ("not_paid", "partial", "in_payment")),
            ], order="date asc, id asc")
        return moves

    def _auto_reconcile_linked_payments(self):
        for cheque in self:
            for payment in (cheque.payment_ids | cheque.payment_id):
                if not payment.move_id or payment.move_id.state != "posted":
                    continue
                matched_invoice_moves = self.env["account.move"]
                payment_arap_lines = payment.move_id.line_ids.filtered(
                    lambda l: l.account_id.account_type in ("asset_receivable", "liability_payable")
                )
                payment_lines = payment.move_id.line_ids.filtered(
                    lambda l: l.account_id.account_type in ("asset_receivable", "liability_payable")
                    and not l.reconciled
                    and l.partner_id
                )
                if not payment_lines:
                    reconciled_counterparts = (
                        payment_arap_lines.filtered(lambda l: l.reconciled).matched_debit_ids.debit_move_id
                        | payment_arap_lines.filtered(lambda l: l.reconciled).matched_credit_ids.credit_move_id
                    )
                    matched_invoice_moves |= (
                        reconciled_counterparts.mapped("move_id") - payment.move_id
                    ).filtered(lambda m: m.is_invoice(True))
                    if matched_invoice_moves:
                        matched_invoice_moves.matched_payment_ids += payment
                    continue

                candidate_moves = cheque._get_candidate_invoice_moves(payment)
                candidate_lines = candidate_moves.line_ids.filtered(
                    lambda l: l.account_id.account_type in ("asset_receivable", "liability_payable")
                    and not l.reconciled
                    and l.partner_id == payment.partner_id
                )
                if not candidate_lines:
                    continue

                for payment_line in payment_lines:
                    if payment_line.reconciled:
                        continue
                    lines = candidate_lines.filtered(
                        lambda l: l.account_id == payment_line.account_id and (l.balance * payment_line.balance) < 0
                    )
                    if not lines:
                        continue
                    exact_line = lines.filtered(
                        lambda l: payment.company_id.currency_id.compare_amounts(
                            abs(l.amount_residual), abs(payment_line.amount_residual)
                        ) == 0
                    )[:1]
                    target_line = exact_line or lines[:1]
                    matched_invoice_moves |= target_line.move_id.filtered(lambda m: m.is_invoice(True))
                    (payment_line | target_line).reconcile()

                # Keep payment smart button on invoices by linking matched payments explicitly.
                # (Core register wizard does this in _reconcile_payments; this flow reconciles later.)
                if not matched_invoice_moves:
                    reconciled_counterparts = (
                        payment_arap_lines.filtered(lambda l: l.reconciled).matched_debit_ids.debit_move_id
                        | payment_arap_lines.filtered(lambda l: l.reconciled).matched_credit_ids.credit_move_id
                    )
                    matched_invoice_moves |= (
                        reconciled_counterparts.mapped("move_id") - payment.move_id
                    ).filtered(lambda m: m.is_invoice(True))

                if matched_invoice_moves:
                    matched_invoice_moves.matched_payment_ids += payment

    def _refresh_linked_invoices_payment_state(self, payments):
        invoices = (payments.reconciled_invoice_ids | payments.invoice_ids).filtered(
            lambda inv: inv.move_type in ('out_invoice', 'in_invoice')
        )
        if invoices:
            invoices._compute_payment_state()
            if hasattr(invoices, '_compute_status_in_payment'):
                invoices._compute_status_in_payment()
        return invoices

    def _set_linked_payments_state_after_cheque_flow(self, payments, target_state, matched=False):
        """Use payment-side helper when available, fallback to minimal write."""
        if not payments:
            return
        helper = getattr(payments, '_cheque_mark_state_after_external_flow', None)
        if helper:
            helper(target_state, matched=matched)
            return
        payments.write({'state': target_state, 'is_matched': matched})
        self._refresh_linked_invoices_payment_state(payments)

    def write(self, vals):
        if 'cheque_date' in vals and 'date' not in vals:
            for rec in self.filtered(lambda r: r.cheque_type == 'inbound'):
                vals['date'] = vals['cheque_date']
        elif 'date' in vals and 'cheque_date' not in vals:
            for rec in self.filtered(lambda r: r.cheque_type == 'inbound'):
                vals['cheque_date'] = vals['date']
        res = super(ChequeInboundOutbound, self).write(vals)
        if 'name' in vals:
            for rec in self:
                rec.cheque_id.name = rec.name
        return res

    def _reverse_moves_for_cancel(self, moves, reason, reverse_date):
        if not moves:
            return self.env['account.move']
        if any(move.state != 'posted' for move in moves):
            raise UserError(_('Only posted journal entries can be reversed.'))

        new_moves = self.env['account.move']
        for journal in moves.mapped('journal_id'):
            journal_moves = moves.filtered(lambda m: m.journal_id == journal)
            default_values_list = [{
                'date': reverse_date,
                'ref': reason,
                'journal_id': journal.id,
            } for _m in journal_moves]
            # Keep source entry posted and create a separate posted reverse entry.
            created_moves = journal_moves._reverse_moves(default_values_list, cancel=False)

            draft_moves = created_moves.filtered(lambda m: m.state == 'draft')
            if draft_moves:
                draft_moves.action_post()
            new_moves |= created_moves
        return new_moves

    def action_cancel(self):
        for cheque in self:
            if cheque.state not in ['return', 'bank_deposit', 'paid']:
                raise UserError(_('Cancel is only available in Void, Deposited, or Paid state.'))

            reverse_date = cheque.return_date or fields.Date.context_today(cheque)
            reversal_moves = self.env['account.move']

            # 1) Identify all posted moves to reverse.
            # - Clearing entry
            moves_to_reverse = (cheque.cheque_validation_entry_id | cheque.cheque_journal_entry_id).filtered(lambda m: m.state == 'posted')
            # - Payment entry (posted at deposit stage)
            payments = cheque.payment_ids | cheque.payment_id
            invoices_to_refresh = (payments.reconciled_invoice_ids | payments.invoice_ids).filtered(
                lambda inv: inv.move_type in ('out_invoice', 'in_invoice')
            )
            posted_payment_moves = payments.mapped('move_id').filtered(lambda m: m.state == 'posted')
            moves_to_reverse |= posted_payment_moves

            if moves_to_reverse:
                # 2) Unreconcile first so linked invoices/bills can be reopened correctly.
                reconciled_lines = moves_to_reverse.line_ids.filtered(lambda line: line.reconciled)
                if reconciled_lines:
                    reconciled_lines.remove_move_reconcile()

                # 3) Reverse each source move (keep source move posted, create reversal move).
                for move in moves_to_reverse:
                    # Always create a new reversal entry on each void action.
                    reason = _('Cancel cheque %s: reverse %s') % (cheque.name, move.name)
                    rev_move = cheque._reverse_moves_for_cancel(move, reason, reverse_date)

                    if rev_move:
                        rev_move.write({
                            'cheque_inbound_outbound_id': cheque.id,
                            'status': 'cancel',
                        })
                        reversal_moves |= rev_move

                # 4) Keep cancel links cumulative for audit history across multiple void/reset cycles.
                latest_deposit_moves = cheque._get_latest_reversal_moves(cheque.cheque_validation_entry_id | cheque.cheque_journal_entry_id)
                existing_deposit_cancel_moves = cheque.cancel_deposit_move_ids.filtered(
                    lambda m: (not m.cheque_inbound_outbound_id or m.cheque_inbound_outbound_id == cheque)
                )
                cheque.cancel_deposit_move_ids = [(6, 0, (latest_deposit_moves | existing_deposit_cancel_moves).ids)]

                payment_moves = (payments.mapped('move_id') if payments else self.env['account.move'])
                latest_payment_moves = cheque._get_latest_reversal_moves(payment_moves)
                existing_payment_cancel_moves = cheque.cancel_payment_move_ids.filtered(
                    lambda m: (not m.cheque_inbound_outbound_id or m.cheque_inbound_outbound_id == cheque)
                )
                cheque.cancel_payment_move_ids = [(6, 0, (latest_payment_moves | existing_payment_cancel_moves).ids)]

                if reversal_moves:
                    move_links = Markup(', ').join([move._get_html_link() for move in reversal_moves])
                    body_msg = Markup('Cancel reversal created and posted for: %s.') % move_links
                    cheque.message_post(
                        body=body_msg,
                        message_type="notification",
                        subtype_id=self.env.ref("mail.mt_comment").id,
                    )

            if payments:
                # Business request: on Void, payment record must be cancelled too.
                # Keep journal entries as posted+reversal, change payment lifecycle state.
                cheque._set_linked_payments_state_after_cheque_flow(payments, 'canceled', matched=False)
            if invoices_to_refresh:
                invoices_to_refresh._compute_payment_state()
                if hasattr(invoices_to_refresh, '_compute_status_in_payment'):
                    invoices_to_refresh._compute_status_in_payment()

            cheque.state = 'cancelled'
            if cheque.cheque_id:
                # Business request: allow reusing the same cheque number after void.
                # Audit remains on cheque transactions/journal entries; cheque book line becomes available again.
                cheque.cheque_id.status = 'draft'

    def _count_transform_cheque(self):
        for cheque in self:
            cheque.count_transform_cheque = 0

    def action_view_trnasform_cheques(self):
        return self._get_action_view_trnasform_cheques(self.cheque_transform_cheque_ids)

    def _get_action_view_journal_moves(self, moves, name):
        action = self.env["ir.actions.actions"]._for_xml_id("cheque_management.act_account_move_cheque")
        action.update({
            'name': name,
            'domain': [('id', 'in', moves.ids)],
            'view_mode': 'list,form',
        })
        context = dict(self.env.context or {})
        context.pop('search_default_cheque_inbound_outbound_id', None)
        context.pop('default_cheque_inbound_outbound_id', None)
        context.update({'create': 0, 'edit': 0, 'cheque_move_view': True})
        action['context'] = context
        return action

    def action_view_transform_entries(self):
        moves = self.env['account.move'].search([
            ('cheque_inbound_outbound_id', 'in', self.ids),
            ('status', '=', 'transform'),
        ])
        moves |= self.mapped('cheque_transfrom_journal_entry_id')
        if not moves:
            return {'type': 'ir.actions.act_window_close'}
        return self._get_action_view_journal_moves(moves, _('Transform Journal Entry'))

    def action_view_void_entries(self):
        moves = self.env['account.move'].search([
            ('cheque_inbound_outbound_id', 'in', self.ids),
            ('status', '=', 'void'),
        ])
        legacy_void_moves = self.mapped('cheque_return_journal_move_id').filtered(lambda m: m.status != 'cancel')
        moves |= legacy_void_moves
        if not moves:
            return {'type': 'ir.actions.act_window_close'}
        return self._get_action_view_journal_moves(moves, _('Void Journal Entry'))

    def action_view_bank_deposit_entries(self):
        moves = self.mapped('cheque_journal_entry_id')
        if not moves:
            return {'type': 'ir.actions.act_window_close'}
        return self._get_action_view_journal_moves(moves, _('Bank Deposit Entry'))

    def action_view_cancel_deposit_entries(self):
        moves = self.env['account.move']
        for cheque in self:
            moves |= cheque._get_latest_reversal_moves(cheque.cheque_validation_entry_id | cheque.cheque_journal_entry_id)
            moves |= cheque.cancel_deposit_move_ids.filtered(
                lambda m: (not m.cheque_inbound_outbound_id or m.cheque_inbound_outbound_id == cheque)
            )
        if not moves:
            return {'type': 'ir.actions.act_window_close'}
        return self._get_action_view_journal_moves(moves, _('Cancel Deposit Entry'))

    def action_view_cancel_payment_entries(self):
        moves = self.env['account.move']
        for cheque in self:
            payment_moves = (cheque.payment_ids | cheque.payment_id).mapped('move_id')
            moves |= cheque._get_latest_reversal_moves(payment_moves)
            moves |= cheque.cancel_payment_move_ids.filtered(
                lambda m: (not m.cheque_inbound_outbound_id or m.cheque_inbound_outbound_id == cheque)
            )
        if not moves:
            return {'type': 'ir.actions.act_window_close'}
        return self._get_action_view_journal_moves(moves, _('Cancel Payment Entry'))

    def action_view_reversed_entries(self):
        moves = self.env['account.move']
        for cheque in self:
            moves |= cheque._get_all_reversed_moves()
        if not moves:
            return {'type': 'ir.actions.act_window_close'}
        return self._get_action_view_journal_moves(moves, _('Reversed Entry'))

    def _get_action_view_trnasform_cheques(self, transform_cheque):
        if self.cheque_type == 'inbound':
            action = self.env["ir.actions.actions"]._for_xml_id("cheque_management.action_cheque_inbound_outbound_receiving")
        else:
            action = self.env["ir.actions.actions"]._for_xml_id("cheque_management.action_cheque_inbound_outbound_paying")

        if len(transform_cheque) > 1:
            action['domain'] = [('id', 'in', transform_cheque.ids)]
        elif transform_cheque:
            form_view = [(self.env.ref('cheque_management.cheque_inbound_outbound_form_view').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = transform_cheque.id
        return action

    def action_view_original_cheques(self):
        cheque = self.original_cheque_transform_id

        if self.cheque_type == 'inbound':
            action = self.env.ref('cheque_management.action_cheque_inbound_outbound_receiving').sudo()
        else:
            action = self.env.ref('cheque_management.action_cheque_inbound_outbound_paying').sudo()
        result = action.read()[0]
        if len(cheque) > 1:
            result['domain'] = [('id', 'in', cheque.ids)]
        elif len(cheque) == 1:
            res = self.env.ref('cheque_management.cheque_inbound_outbound_form_view', False)
            form_view = [(res and res.id or False, 'form')]
            if 'views' in result:
                result['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                result['views'] = form_view
            result['res_id'] = cheque.id
        else:
            result = {'type': 'ir.actions.act_window_close'}
        result['context'] = {'create': 0}
        return result

    def action_validate(self):
        for rec in self:
            if rec.state == 'bank_deposit':
                move = rec._ensure_bank_deposit_entry()
                _bank_account, outstanding_account = rec._get_bank_and_outstanding_accounts()
                payments = rec.payment_ids | rec.payment_id
                if payments and outstanding_account:
                    payment_outstanding_lines = payments.mapped('move_id.line_ids').filtered(
                        lambda l: l.account_id.id == outstanding_account.id and not l.reconciled
                    )
                    done_outstanding_line = move.line_ids.filtered(
                        lambda l: l.account_id.id == outstanding_account.id and not l.reconciled
                    )
                    if payment_outstanding_lines and done_outstanding_line:
                        (payment_outstanding_lines + done_outstanding_line).reconcile()

            # IMPORTANT: set cheque state first so invoice payment_state computes can see cheque == 'paid'
            # and flip invoices from in_payment -> paid in the same action.
            rec.state = 'paid'

            # Process linked payments if any
            payments = rec.payment_ids | rec.payment_id
            if payments:
                rec._set_linked_payments_state_after_cheque_flow(payments, 'paid', matched=True)
                # Some helpers/fallbacks refresh invoice states before cheque state is updated.
                # Recompute once more after state='paid' to keep invoice ribbon/state consistent.
                rec._refresh_linked_invoices_payment_state(payments)

    def action_transform_cheque(self):
        for cheque in self:
            moves = cheque.cheque_return_journal_move_id
            if not moves:
                payments = (cheque.payment_ids | cheque.payment_id).filtered('move_id')
                if not payments:
                    raise UserError(_('No payment journal entry found to reverse.'))
                moves = payments.mapped('move_id')
            if any(move.state != 'posted' for move in moves):
                raise UserError(_('Only posted journal entries can be reversed.'))

            reverse_date = cheque.transform_date or fields.Date.context_today(cheque)
            reversal_wizard = self.env['account.move.reversal'].create({
                'move_ids': [(6, 0, moves.ids)],
                'date': reverse_date,
                'company_id': cheque.company_id.id,
                'journal_id': moves[:1].journal_id.id,
            })
            reversal_wizard.refund_moves()
            new_moves = reversal_wizard.new_move_ids
            if new_moves:
                new_moves.write({
                    "status": "transform",
                    "cheque_inbound_outbound_id": cheque.id,
                })
            if new_moves:
                move_links = Markup(', ').join([move._get_html_link() for move in new_moves])
                body_msg = Markup('Transform entry created: %s.') % move_links
                cheque.message_post(body=body_msg,
                                    message_type="notification",
                                    subtype_id=self.env.ref("mail.mt_comment").id)
            if len(new_moves) == 1:
                cheque.cheque_transfrom_journal_entry_id = new_moves.id
            cheque.state = 'transform'

    def action_transform(self):
        if not self.transform_detail_lines:
            raise UserError(_('Please Add transform lines first.'))

        amount = 0.0
        for amount_check in self.transform_detail_lines:
            if amount_check.use_cheque:
                amount += amount_check.amount
        if self.amount < amount:
            raise UserError(_('Amount must be less than cheque amount'))

        if self.balance < 0.0:
            raise UserError(_('Balance amount should not be negative'))

        transform_cheque_list = []

        for line in self.transform_detail_lines:
            if line.use_cheque:
                if line.cheque_type == 'inbound':
                    new_cheque_paying = self.env['cheque.inbound.outbound'].create({
                        'name': line.cheque_id.name,
                        'cheque_id': line.cheque_id.id,
                        'cheque_book_id': line.cheque_id.cheque_book_id.id,
                        'cheque_type': 'inbound',
                        'bank_account_journal_id': line.payment_method_id.id,
                        'pay_partner_id': self.pay_partner_id.id,
                        'partner_name': self.pay_partner_id.name,
                        'ac_payee': line.ac_payee,
                        'memo': line.remark,
                        'amount': line.amount,
                        'cheque_date': line.date,
                        'date': line.date,
                        'payment_id': line.cheque_inbound_outbound_id.payment_id.id,
                        'original_cheque_transform_id': self.id,
                        'payment_method_line_id': line.payment_method_line_id.id,
                    })
                    self.env['cheque.payment.detail.lines'].create({
                        'payment_ref': line.cheque_inbound_outbound_id.payment_id.id,
                        'date': line.cheque_inbound_outbound_id.payment_id.date,
                        'currency_id': line.cheque_inbound_outbound_id.payment_id.currency_id.id,
                        'amount': line.cheque_inbound_outbound_id.payment_id.amount,
                        'total_amount': line.cheque_inbound_outbound_id.payment_id.amount,
                        'cheque_inbound_outbound_id': new_cheque_paying.id,
                    })
                    transform_cheque_list.append(new_cheque_paying.id)
                    new_cheque_paying.action_waiting_confirm()
                    line.cheque_id.status = 'waiting_confirm'
                    line.cheque_id.date = line.date
                    line.cheque_id.pay_to = self.pay_partner_id.id
                    line.cheque_id.amount = line.amount
                    line.cheque_id.memo = line.remark
                elif line.cheque_type == 'outbound':
                    new_cheque_paying = self.env['cheque.inbound.outbound'].create({
                        'name': line.receiving_cheque_id,
                        'cheque_type': 'outbound',
                        'bank_account_journal_id': line.payment_method_id.id,
                        'pay_partner_id': self.pay_partner_id.id,
                        'partner_name': self.pay_partner_id.name,
                        'ac_payee': line.ac_payee,
                        'memo': line.remark,
                        'amount': line.amount,
                        'cheque_date': line.date,
                        'date': line.date,
                        'payment_id': line.cheque_inbound_outbound_id.payment_id.id,
                        'original_cheque_transform_id': self.id,
                        'payment_method_line_id': line.payment_method_line_id.id,
                    })
                    self.env['cheque.payment.detail.lines'].create({
                        'payment_ref': line.cheque_inbound_outbound_id.payment_id.id,
                        'date': line.cheque_inbound_outbound_id.payment_id.date,
                        'currency_id': line.cheque_inbound_outbound_id.payment_id.currency_id.id,
                        'amount': line.cheque_inbound_outbound_id.payment_id.amount,
                        'total_amount': line.cheque_inbound_outbound_id.payment_id.amount,
                        'cheque_inbound_outbound_id': new_cheque_paying.id,
                    })
                    transform_cheque_list.append(new_cheque_paying.id)
                    new_cheque_paying.action_waiting_confirm()
        self.cheque_transform_cheque_ids = [(6, 0, transform_cheque_list)]
        self.action_cancel()
        self.cheque_id.status = 'cancelled'

        # Create Journal Entries
        credit_line = debit_line = ''
        Move = self.env['account.move']
        for transform_line in self.transform_detail_lines:
            if self.cheque_type == 'inbound':
                if transform_line.use_cheque:
                    credit_line = {
                        'account_id': transform_line.payment_method_line_id.payment_account_id.id,
                        'partner_id': self.pay_partner_id.id,
                        'name': 'Transform Cheque no ' + str(transform_line.cheque_id.name),
                        'debit': 0,
                        'credit': transform_line.amount,
                        'date_maturity': self.transform_date,
                    }
                    debit_line = {
                        'account_id': transform_line.payment_method_line_id.payment_account_id.id,
                        'partner_id': self.pay_partner_id.id,
                        'name': 'Cancelled Cheque no ' + str(self.name),
                        'debit': transform_line.amount,
                        'credit': 0,
                        'date_maturity': self.cheque_date,
                    }
                    move_vals = {
                        'date': self.transform_date or fields.Date.context_today(self),
                        'journal_id': self.bank_account_journal_id.id,
                        'ref': 'Transform Cheque from ' + str(self.name),
                        'line_ids': [(0, 0, credit_line), (0, 0, debit_line)],
                        'cheque_inbound_outbound_id': self.id
                    }
                    move_id = Move.create(move_vals)
                    move_id.action_post()
                else:
                    credit_line = {
                        'account_id': transform_line.payment_method_line_id.payment_account_id.id,
                        'partner_id': self.pay_partner_id.id,
                        'name': 'Transform Cheque from ' + str(self.payment_method_line_id.name),
                        'debit': 0,
                        'credit': transform_line.amount,
                        'date_maturity': self.transform_date,
                    }
                    debit_line = {
                        'account_id': self.payment_method_line_id.payment_account_id.id,
                        'partner_id': self.pay_partner_id.id,
                        'name': 'Cancelled Cheque no ' + str(self.name),
                        'debit': transform_line.amount,
                        'credit': 0,
                        'date_maturity': self.cheque_date,
                    }
                    move_vals = {
                        'date': self.transform_date or fields.Date.context_today(self),
                        'journal_id': self.bank_account_journal_id.id,
                        'ref': 'Transform Cheque from ' + str(self.name),
                        'line_ids': [(0, 0, credit_line), (0, 0, debit_line)],
                        'cheque_inbound_outbound_id': self.id
                    }
                    move_id = Move.create(move_vals)
                    move_id.action_post()
            elif self.cheque_type == 'outbound':
                if transform_line.use_cheque:
                    credit_line = {
                        'account_id': transform_line.payment_method_line_id.payment_account_id.id,
                        'partner_id': self.pay_partner_id.id,
                        'name': 'Transform Cheque no ' + str(transform_line.cheque_id.name),
                        'debit': 0,
                        'credit': transform_line.amount,
                        'date_maturity': self.transform_date,
                    }
                    debit_line = {
                        'account_id': transform_line.payment_method_id.payment_debit_account_id.id,
                        'partner_id': self.pay_partner_id.id,
                        'name': 'Cancelled Cheque no ' + str(self.name),
                        'debit': transform_line.amount,
                        'credit': 0,
                        'date_maturity': self.cheque_date,
                    }
                    move_vals = {
                        'date': self.transform_date or fields.Date.context_today(self),
                        'journal_id': self.bank_account_journal_id.id,
                        'ref': 'Transform Cheque from ' + str(self.name),
                        'line_ids': [(0, 0, credit_line), (0, 0, debit_line)],
                        'cheque_inbound_outbound_id': self.id
                    }
                    move_id = Move.create(move_vals)
                    move_id.action_post()
                else:
                    credit_line = {
                        'account_id': self.payment_method_id.payment_debit_account_id.id,
                        'partner_id': self.pay_partner_id.id,
                        'name': 'Transform Cheque from ' + str(self.payment_method_line_id.name),
                        'debit': 0,
                        'credit': transform_line.amount,
                        'date_maturity': self.transform_date,
                    }
                    debit_line = {
                        'account_id': transform_line.payment_method_line_id.payment_account_id.id,
                        'partner_id': self.pay_partner_id.id,
                        'name': 'Cancelled Cheque no ' + str(self.name),
                        'debit': transform_line.amount,
                        'credit': 0,
                        'date_maturity': self.cheque_date,
                    }
                    move_vals = {
                        'date': self.transform_date or fields.Date.context_today(self),
                        'journal_id': self.bank_account_journal_id.id,
                        'ref': 'Transform Cheque from ' + str(self.name),
                        'line_ids': [(0, 0, credit_line), (0, 0, debit_line)],
                        'cheque_inbound_outbound_id': self.id
                    }
                    move_id = Move.create(move_vals)
                    move_id.action_post()

    def action_reset_to_draft(self):
        for rec in self:
            linked_moves = (
                rec.cheque_journal_entry_id
                | rec.cheque_validation_entry_id
                | rec.cheque_transfrom_journal_entry_id
                | rec.cheque_return_journal_move_id
                | rec._get_all_reversed_moves()
                | (rec.payment_ids | rec.payment_id).mapped('move_id')
            ).filtered(lambda m: m.state == 'posted')
            rec.state = 'draft'
            rec.cheque_optinal = False
            rec.return_date = False
            rec.void_reason = False
            # Keep posted move links for audit traceability. Only clear pointers when no posted moves exist.
            if not linked_moves:
                rec.cheque_journal_entry_id = False
                rec.cheque_validation_entry_id = False
            if rec.cheque_id:
                rec.cheque_id.status = 'draft'

            # Business request: after reset to draft, payment should come back to in payment.
            payments = rec.payment_ids | rec.payment_id
            if payments:
                rec._set_linked_payments_state_after_cheque_flow(payments, 'in_process', matched=False)

    def action_bank_deposit(self):
        for rec in self:
            if rec.cheque_type not in ('outbound', 'inbound'):
                raise UserError(_('Bank Deposit is only available for cheque payments.'))
            if not rec.bank_account_journal_id:
                raise UserError(_('Please set Bank Account Journal before bank deposit.'))
            if not rec.amount or rec.amount <= 0:
                raise UserError(_('Cheque amount must be greater than zero.'))

            # Post linked payments now (at Deposit stage)
            payments = rec.payment_ids | rec.payment_id
            if payments:
                # Post only payments whose journal entry is still draft.
                draft_payments = payments.filtered(
                    lambda p: p.move_id and p.move_id.state == 'draft'
                )
                if draft_payments:
                    draft_payments.with_context(force_post_cheque=True).action_post()
            rec._auto_reconcile_linked_payments()

            body_msg = Markup('Cheque state changed to Bank Deposit. Linked payments posted.')
            rec.message_post(body=body_msg, message_type="notification", subtype_id=self.env.ref("mail.mt_comment").id)
            rec.state = 'bank_deposit'


    # --- Batch Actions (Restored) ---
    def action_state_deposit(self):
        active_ids = self.env.context.get('active_ids')
        if not active_ids:
            return
        cheques = self.browse(active_ids)
        for cheque in cheques:
            if cheque.state in ['draft', 'waiting_confirm', 'confirmed']:
                if cheque.state != 'confirmed':
                    cheque.action_confirm_pay()
                cheque.action_bank_deposit()

    def action_state_paid(self):
        active_ids = self.env.context.get('active_ids')
        if not active_ids:
            return
        cheques = self.browse(active_ids).filtered(
            lambda c: c.state in ('draft', 'waiting_confirm', 'confirmed', 'bank_deposit')
        )
        if not cheques:
            return
        wizard = self.env['cheque.done.wizard'].create({
            'line_ids': [(0, 0, {'cheque_id': c.id}) for c in cheques],
        })
        return {
            'name': _('Done Cheques - Payment Date'),
            'type': 'ir.actions.act_window',
            'res_model': 'cheque.done.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_state_cancel(self):
        active_ids = self.env.context.get('active_ids')
        if not active_ids:
            return
        cheques = self.browse(active_ids)
        for cheque in cheques:
            if cheque.state not in ['paid', 'cancelled']:
                # Note: original action_cancel checks for 'return' state.
                # For batch, we might need to handle other states or just call the method if valid.
                try:
                    cheque.action_cancel()
                except UserError:
                    continue

    def unlink(self):
        for cheque in self:
            if cheque.state != 'draft':
                raise UserError(_("You cannot delete a cheque which is not in Draft State."))
        return super(ChequeInboundOutbound, self).unlink()

    def print_dynamic_cheque_report(self):
        self.is_cheque_print = True
        self._create_paper_format()
        body_msg = 'Cheque Print by %s.' % (self.env.user.name)
        self.message_post(body=body_msg, message_type="notification", subtype_id=self.env.ref("mail.mt_comment").id)
        return self.env.ref('cheque_management.dynamic_cheque_print_report_action').report_action(self)

    @api.model
    def _create_paper_format(self):
        report_action_id = self.env['ir.actions.report'].sudo().search([('report_name', '=', 'cheque_management.report_dynamic_check_print')])
        if not report_action_id:
            raise Warning('Someone has deleted the reference view of report, Please Update the module!')
        config_rec = self.env['dynamic.cheque'].sudo().search([('name', '=', self.dynamic_io_cheque_id.name)], limit=1)
        if not config_rec:
            raise Warning(_("Report format not found! Please Update Module."))

        page_height = config_rec.cheque_hight or 10
        page_width = config_rec.cheque_width or 10
        margin_top = 3
        margin_bottom = 15
        margin_left = 10
        margin_right = 2
        dpi = 90
        header_spacing = 0
        orientation = 'Portrait'
        self._cr.execute(
            """ DELETE FROM report_paperformat WHERE custom_report=TRUE""")
        paperformat_id = self.env['report.paperformat'].sudo().create({
            'name': 'Custom Report Cheque',
            'format': 'custom',
            'page_height': page_height,
            'page_width': page_width,
            'dpi': dpi,
            'custom_report': True,
            'margin_top': margin_top,
            'margin_bottom': margin_bottom,
            'margin_left': margin_left,
            'margin_right': margin_right,
            'header_spacing': header_spacing,
            'orientation': orientation,
        })
        report_action_id.sudo().write({'paperformat_id': paperformat_id.id})
        return True

    @api.model
    def _amount_in_word_line(self):
        payment_id = self.payment_id
        partner = payment_id.partner_id.name_get()
        partner_id = payment_id.partner_id.display_name
        self.cheque_format.partner_id = partner_id
        amount_word = payment_id.check_amount_in_words
        first_line = (amount_word[0:self.cheque_format.words_in_fl_line])
        self.cheque_format.first_line_amount = first_line
        s1 = self.cheque_format.words_in_fl_line
        s2 = self.cheque_format.words_in_fl_line + self.cheque_format.words_in_sc_line
        second_line = (amount_word[s1:s2])
        self.cheque_format.second_line_amount = second_line


class ChequePaymentDetailLines(models.Model):
    _name = 'cheque.payment.detail.lines'
    _description = 'Cheque Payment Detail Lines'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    cheque_inbound_outbound_id = fields.Many2one('cheque.inbound.outbound', string="Cheque")
    payment_ref = fields.Many2one('account.payment', 'Payment Reference')
    date = fields.Date('Date')
    currency_id = fields.Many2one('res.currency', string='Currency')
    fees_or_charges = fields.Float('Fees/Charges')
    amount = fields.Monetary('Amount')
    total_amount = fields.Monetary('Total Amount', compute='_compute_total_amount', store=True)
    state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, tracking=True, related='payment_ref.state', store=True)

    @api.depends('amount', 'fees_or_charges')
    def _compute_total_amount(self):
        for line in self:
            line.total_amount = line.fees_or_charges + line.amount


class ChequeTransformDetailLines(models.Model):
    _name = 'cheque.transform.detail.lines'
    _description = 'Transform Detail Lines'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    cheque_inbound_outbound_id = fields.Many2one('cheque.inbound.outbound', string="Cheque")
    cheque_type = fields.Selection([('inbound', 'Inbound'),
                                    ('outbound', 'Outbound')], string='Type', tracking=True,
                                    related='cheque_inbound_outbound_id.cheque_type', store=True)
    payment_method_id = fields.Many2one('account.journal', string="Journal", domain="[('type', 'in', ('bank', 'cash'))]")
    payment_method_line_id = fields.Many2one('account.payment.method.line', 'Payment Method')
    use_cheque = fields.Boolean('Use Cheque')
    cheque_id = fields.Many2one('cheque.book.lines', 'Cheque')
    receiving_cheque_id = fields.Char('Cheque')
    branch = fields.Char('Branch')
    date = fields.Date('Date', default=fields.Date.context_today)
    ac_payee = fields.Boolean('A/C Payee', default=False)
    amount = fields.Float('Amount')
    remark = fields.Text('Remark')
    filtered_payment_method_line_ids = fields.Many2many(
        'account.payment.method.line',
        compute='_compute_filtered_payment_method_line_ids',
        string='Payment Methods',
        store=True
    )

    @api.depends('payment_method_id')
    def _compute_filtered_payment_method_line_ids(self):
        for rec in self:
            if rec.cheque_type == 'inbound':
                inbound_payment_method_line = self.env['account.payment.method.line'].search([('journal_id', '=', rec.payment_method_id.id), ('payment_type', '=', 'outbound')])
                rec.filtered_payment_method_line_ids = [(6, 0 , inbound_payment_method_line.ids)]
            if rec.cheque_type == 'outbound':
                outbound_payment_method_line = self.env['account.payment.method.line'].search([('journal_id', '=', rec.payment_method_id.id), ('payment_type', '=', 'inbound')])
                rec.filtered_payment_method_line_ids = [(6, 0 , outbound_payment_method_line.ids)]

    @api.onchange('use_cheque', 'ac_payee')
    def _onchange_use_cheque(self):
        if self.use_cheque == False:
            self.ac_payee = False
