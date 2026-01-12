from odoo import api, fields, models, tools


class ChequeAnalysisReport(models.Model):
    _name = "cheque.analysis.report"
    _description = "Cheque Analysis Report"
    _auto = False
    _order = 'cheque_date desc'

    # Cheque Fields
    name = fields.Char('Cheque No.', readonly=True)
    cheque_type = fields.Selection([('inbound', 'Inbound'),
                                    ('outbound', 'Outbound')], readonly=True)
    bank_account_journal_id = fields.Many2one('account.journal', 'Bank Account', domain=[('type', '=', 'bank')], readonly=True)
    pay_partner_id = fields.Many2one('res.partner', 'Partner', readonly=True)
    cheque_amount = fields.Monetary('Amount', readonly=True)
    payment_date = fields.Date('Payment Date', readonly=True)
    cheque_date = fields.Date('Cheque Date', readonly=True)
    clearing_date = fields.Date('Clearing Date', readonly=True)
    return_date = fields.Date('Return Date', readonly=True)
    transform_date = fields.Date('Transform Date', readonly=True)
    state = fields.Selection([('draft', 'Draft'),
                              ('waiting_confirm', 'Waiting Confirm'),
                              ('confirmed', 'Confirmed'),
                              ('return', 'Return'),
                              ('paid', 'Paid'),
                              ('cancelled', 'Cancelled')], readonly=True)
    payment_id = fields.Many2one('account.payment', 'Payment', readonly=True)
    cheque_book_id = fields.Many2one('cheque.book', string="Cheque Book", readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)

    # Payment Detail Lines
    payment_ref = fields.Many2one('account.payment', 'Payment Reference', readonly=True)
    payment_line_date = fields.Date('Date(Payment Lines)', readonly=True)
    payment_amount = fields.Monetary('Amount(Payment Lines)', readonly=True)
    total_amount = fields.Monetary('Total Amount(Payment Lines)', readonly=True)

    # Transform Detail Lines
    payment_method_id = fields.Many2one('account.journal', string="Payment Method", readonly=True)
    cheque_id = fields.Many2one('cheque.book.lines', 'Cheque', readonly=True)
    receiving_cheque_id = fields.Char('Receiving Cheque', readonly=True)
    branch = fields.Char('Branch', readonly=True)
    transform_line_date = fields.Date('Date(Transform Lines)', readonly=True)
    transform_amount = fields.Integer('Amount(Transform Lines)', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (
            %s
            FROM ( %s )
            %s
            )""" % (self._table, self._select(), self._from(), self._group_by()))

    def _select(self):
        select_str = """
            SELECT
                min(pl.id) as id,
                cio.name,
                cio.date as payment_date,
                cio.cheque_date as cheque_date,
                cio.clearing_date as clearing_date,
                cio.return_date as return_date,
                cio.transform_date as transform_date,
                cio.state,
                cio.pay_partner_id as pay_partner_id,
                cio.bank_account_journal_id as bank_account_journal_id,
                cio.cheque_book_id as cheque_book_id,
                cio.amount as cheque_amount,
                cio.cheque_type,

                pl.payment_ref as payment_ref,
                pl.date as payment_line_date,
                pl.amount as payment_amount,
                pl.total_amount as total_amount,
                
                tl.payment_method_id as payment_method_id,
                tl.cheque_id as cheque_id,
                tl.receiving_cheque_id as receiving_cheque_id,
                tl.branch as branch,
                tl.date as transform_line_date,
                tl.amount as transform_amount
        """
        return select_str

    def _from(self):
        from_str = """
            cheque_payment_detail_lines pl
                join cheque_inbound_outbound cio on (pl.cheque_inbound_outbound_id=cio.id)
                left join cheque_transform_detail_lines tl on (pl.cheque_inbound_outbound_id = tl.cheque_inbound_outbound_id)
        """
        return from_str

    def _group_by(self):
        group_by_str = """
            GROUP BY
                cio.name,
                cio.date,
                cio.cheque_date,
                cio.clearing_date,
                cio.return_date,
                cio.transform_date,
                cio.state,
                cio.pay_partner_id,
                cio.bank_account_journal_id,
                cio.cheque_book_id,
                cio.amount,
                cio.cheque_type,
                pl.payment_ref,
                pl.date,
                pl.amount,
                pl.total_amount,
                tl.payment_method_id,
                tl.cheque_id,
                tl.receiving_cheque_id,
                tl.branch,
                tl.date,
                tl.amount,
                cio.id
        """
        return group_by_str
