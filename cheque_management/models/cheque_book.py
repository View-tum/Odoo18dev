from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError


class ChequeBook(models.Model):
    _name = 'cheque.book'
    _description = 'Cheque Book'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Cheque Book No', readonly=True,copy=False, default='New', tracking=True)
    state = fields.Selection([('draft', 'Draft'),
                              ('submit', 'Submit'),
                              ('done', 'Done'),
                              ('close', 'Close')], default='draft', string='Status', tracking=True)
    date = fields.Date('Date', default=fields.datetime.now())
    bank_account_journal_id = fields.Many2one('account.journal', 'Bank Account', domain=[('type', '=', 'bank'), ('is_cheque_outgoing', '=', True)])
    cheque_qty = fields.Integer('Quantity')
    first_cheque_no = fields.Integer('First Cheque No')
    first_cheque_no_char = fields.Char('First Cheque No Char', default="0")
    last_cheque_no = fields.Integer('Last Cheque No', compute='_compute_last_cheque_no', store=True)
    last_cheque_no_char = fields.Char('Last Cheque No Char', default="0")
    cheque_book_lines = fields.One2many('cheque.book.lines', 'cheque_book_id', 'Cheque Book Lines')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    is_state_close = fields.Boolean('Is state Close?', compute='_compute_is_state_close')

    _sql_constraints = [
        ('check_first_cheque_no_char',
         'check(first_cheque_no_char.isdigit())', 'Enter Only Digits!')
    ]

    @api.onchange('first_cheque_no_char')
    def _onchnage_first_cheque_no_char(self):
        if self.first_cheque_no_char:
            if not self.first_cheque_no_char.isdigit():
                raise ValidationError(_('Enter Only Digits!'))
            self.first_cheque_no = self.first_cheque_no_char

    @api.depends('state', 'cheque_book_lines')
    def _compute_is_state_close(self):
        for record in self:
            record.is_state_close = False
            for line in record.cheque_book_lines:
                if all(line.status != 'draft' for line in record.cheque_book_lines):
                    record.is_state_close = True
                else:
                    record.is_state_close = False
            if record.is_state_close:
                record.state = 'close'

    @api.depends('cheque_qty', 'first_cheque_no')
    def _compute_last_cheque_no(self):
        for line in self:
            if line.cheque_qty > 0 and line.first_cheque_no > 0:
                line.last_cheque_no = line.cheque_qty + line.first_cheque_no - 1
                if line.first_cheque_no_char.startswith("0"):
                    line.last_cheque_no_char = str(line.last_cheque_no).zfill(
                        len(line.first_cheque_no_char))
                else:
                    line.last_cheque_no_char = line.last_cheque_no

    def action_submit(self):
        if self.name == 'New':
            self.name = self.env['ir.sequence'].next_by_code(
                'cheque.book') or 'New'
        self.state = 'submit'

    def action_generate_cheque(self):
        self.cheque_book_lines.unlink()
        first_cheque_no = self.first_cheque_no
        while first_cheque_no <= self.last_cheque_no:
            self.env['cheque.book.lines'].create({
                'name': str(first_cheque_no).zfill(len(self.first_cheque_no_char)),
                'cheque_book_id': self.id,
            })
            first_cheque_no += 1

    def action_clear_cheque(self):
        self.cheque_book_lines.unlink()

    def action_confirm(self):
        if not self.cheque_book_lines:
            self.action_generate_cheque()
        self.state = 'done'

    def unlink(self):
        for cheque_book in self:
            if cheque_book.state != 'draft':
                raise UserError(_("You cannot delete a cheque book which is not in Draft State."))
        return super(ChequeBook, self).unlink()

    def generate_cheque_lists_history(self):
        self._cr.execute("""DELETE FROM cheque_lists_history""")
        vals = {}
        cheque_book_ids = self.env['cheque.book'].search([])
        for record in cheque_book_ids:
            for line in record.cheque_book_lines:
                vals.update({
                    'bank_account_journal_id': record.bank_account_journal_id.id,
                    'cheque_book_no': record.name,
                    'date': record.date,
                    'cheque_book_id': record.id,
                    'cheque_no': line.name,
                    'cheque_date': line.date,
                    'pay_to': line.pay_to.id,
                    'amount': line.amount,
                    'memo': line.memo,
                    'currency_id': line.currency_id.id,
                    'status': line.status,
                    'company_id': record.company_id.id,
                })
            cheque_lists_obj = self.env['cheque.lists.history'].create(vals)


class ChequeBookLines(models.Model):
    _name = 'cheque.book.lines'
    _description = 'Cheque Book Lines'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    cheque_book_id = fields.Many2one('cheque.book', 'Cheque Book')
    bank_account_journal_id = fields.Many2one('account.journal', 'Bank Account', related='cheque_book_id.bank_account_journal_id', store=True)
    name = fields.Char('Cheque No')
    date = fields.Date('Cheque Date')
    pay_to = fields.Many2one('res.partner', 'Pay To')
    amount = fields.Monetary('Amount')
    memo = fields.Char('Memo')
    status = fields.Selection([('draft', 'Available'),
                               ('waiting_confirm', 'Waiting Confirm'),
                               ('confirmed', 'Confirmed'),
                               ('return', 'Return'),
                               ('paid', 'Paid'),
                               ('cancelled', 'Cancelled')], default='draft', string='Status', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        help='Utility field to express amount currency',
        default=lambda self: self.env.company.currency_id,
        readonly=True,
    )
    is_state_draft = fields.Boolean('Is state Draft?', compute='_compute_state')
    is_state_waiting_confirm = fields.Boolean('Is state Waiting Confirm?', compute='_compute_state')
    is_state_return = fields.Boolean('Is state Return?', compute='_compute_state')
    is_state_paid = fields.Boolean('Is state Paid?', compute='_compute_state')
    is_state_cancelled = fields.Boolean('Is state Cancelled?', compute='_compute_state')

    @api.depends('cheque_book_id')
    def _compute_state(self):
        for record in self:
            record.is_state_draft = False
            record.is_state_waiting_confirm = False
            record.is_state_return = False
            record.is_state_paid = False
            record.is_state_cancelled = False

            cheque_in_out_bound_obj = self.env['cheque.inbound.outbound'].search([('cheque_id', '=', record.id)])
            if cheque_in_out_bound_obj:
                for line in cheque_in_out_bound_obj:
                    if line.state == 'draft':
                        record.is_state_draft = True
                        if record.is_state_draft:
                            record.status = 'draft'
                    if line.state == 'waiting_confirm':
                        record.is_state_waiting_confirm = True
                        if record.is_state_waiting_confirm:
                            record.status = 'waiting_confirm'
                    if line.state == 'return':
                        record.is_state_return = True
                        if record.is_state_return:
                            record.status = 'return'
                    if line.state == 'paid':
                        record.is_state_paid = True
                        if record.is_state_paid:
                            record.status = 'paid'
                    if line.state == 'cancelled':
                        record.is_state_cancelled = True
                        if record.is_state_cancelled:
                            record.status = 'cancelled'

    def unlink(self):
        for rec in self:
            if rec.status != 'draft':
                raise ValidationError(_("You can't delete the recod except Available!"))
        return super(ChequeBookLines, self).unlink()

    def action_reset_to_draft(self):
        self.update({'status': 'draft'})
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_cancel(self):
        self.update({'status': 'cancelled'})
        return {'type': 'ir.actions.client', 'tag': 'reload'}
