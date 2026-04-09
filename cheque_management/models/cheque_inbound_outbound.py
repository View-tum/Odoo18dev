from odoo import models, fields, api, _
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
    partner_name = fields.Char('Partner')
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
                              ('return', 'Void'),
                              ('paid', 'Paid'),
                              ('cancelled', 'Cancelled')], default='draft', string='Status', tracking=True)
    payment_id = fields.Many2one('account.payment', 'Payment')
    payment_ids = fields.Many2many('account.payment', string='Payments')
    count_payment = fields.Integer(compute='_count_payment', string='Payments')
    count_move = fields.Integer(compute='_count_move', string='Journals')

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
            cheque.count_payment = len(cheque.payment_ids)

    def action_view_payment_cheque(self):
        return self._get_action_view_payment_cheque(self.payment_ids)

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
            cheque.count_move = self.env['account.move'].search_count([('cheque_inbound_outbound_id', '=', self.id)])

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

    def action_confirm_pay(self):
        # if not self.clearing_date and not self.cheque_optinal in ['return', 'transform']:
        #     raise UserError(_('Please Add Clearing date. It must be required.'))
        cheque_book_lines_id = self.env['cheque.book.lines'].search([('name', '=', self.cheque_id.name)])
        self.state = 'confirmed'
        self.cheque_id.status = 'confirmed'

    def write(self, vals):
        res = super(ChequeInboundOutbound, self).write(vals)
        if 'name' in vals:
            for rec in self:
                rec.cheque_id.name = rec.name
        return res

    def action_cancel(self):
        self.state = 'cancelled'

    def _count_transform_cheque(self):
        for cheque in self:
            cheque.count_transform_cheque = len(cheque.cheque_transform_cheque_ids)

    def action_view_trnasform_cheques(self):
        return self._get_action_view_trnasform_cheques(self.cheque_transform_cheque_ids)

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
            if not rec.clearing_date and rec.cheque_optinal not in ['return', 'transform']:
                raise UserError(_('Please Add Clearing date. It must be required.'))
    
            rec.state = 'paid'
            if rec.cheque_id:
                rec.cheque_id.status = 'paid'

            # Mark linked payments as cleared so invoices can move out of 'in_payment'
            payments = rec.payment_ids | rec.payment_id
            if payments:
                payments.write({'state': 'paid', 'is_matched': True})
                invoices = (payments.reconciled_invoice_ids | payments.invoice_ids).filtered(
                    lambda inv: inv.move_type in ('out_invoice', 'in_invoice')
                )

                # Try to reconcile outstanding open items between payment and invoice lines for matching accounts.
                payment_lines = payments.mapped('move_id.line_ids').filtered(
                    lambda l: l.account_id.reconcile and not l.reconciled
                )
                for invoice in invoices:
                    inv_lines = invoice.line_ids.filtered(lambda l: l.account_id.reconcile and not l.reconciled)
                    for account in inv_lines.account_id:
                        lines = inv_lines.filtered(lambda l: l.account_id == account) | payment_lines.filtered(
                            lambda l: l.account_id == account
                        )
                        if len(lines) >= 2:
                            lines.reconcile()

                if invoices:
                    invoices._compute_payment_state()
                    invoices._compute_status_in_payment()
                    invoices.write({'payment_state': 'paid', 'status_in_payment': 'paid'})
                    

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
                        'date': fields.Date.today(),
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
                        'date': fields.Date.today(),
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
                        'date': fields.Date.today(),
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
                        'date': fields.Date.today(),
                        'journal_id': self.bank_account_journal_id.id,
                        'ref': 'Transform Cheque from ' + str(self.name),
                        'line_ids': [(0, 0, credit_line), (0, 0, debit_line)],
                        'cheque_inbound_outbound_id': self.id
                    }
                    move_id = Move.create(move_vals)
                    move_id.action_post()

    def action_reset_to_draft(self):
        self.state = 'draft'

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
