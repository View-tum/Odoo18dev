from odoo import api, fields, models

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    payment_count = fields.Integer(
        string="Payments",
        compute="_compute_payment_count",
        store=False
    )

    payment_total_amount = fields.Monetary(
        string="ยอดชำระแล้ว",
        compute="_compute_payment_total",
        currency_field='currency_id',
        store=False
    )

    has_payment = fields.Boolean(
        string="Has Payments",
        compute="_compute_has_payment",
        store=False
    )

    @api.depends('invoice_ids')
    def _compute_payment_count(self):
        for order in self:
            all_invoices = order.invoice_ids | self.env['account.move'].search([
                ('invoice_origin', '=', order.name),
                ('move_type', 'in', ['out_invoice', 'out_refund'])
            ])
            payments = self.env['account.payment'].search([
                ('invoice_ids', 'in', all_invoices.ids)
            ])
            order.payment_count = len(payments)

    @api.depends('payment_count')
    def _compute_has_payment(self):
        for order in self:
            order.has_payment = order.payment_count > 0

    @api.depends('invoice_ids')
    def _compute_payment_total(self):
        for order in self:
            all_invoices = order.invoice_ids | self.env['account.move'].search([
                ('invoice_origin', '=', order.name),
                ('move_type', 'in', ['out_invoice', 'out_refund'])
            ])
            payments = self.env['account.payment'].search([
                ('invoice_ids', 'in', all_invoices.ids)
            ])
            order.payment_total_amount = sum(pay.amount for pay in payments)

    def action_view_payments(self):
        if self.payment_count == 0:
            return False  # ไม่สร้าง action ถ้าไม่มี payment
        self.ensure_one()
        all_invoices = self.invoice_ids | self.env['account.move'].search([
            ('invoice_origin', '=', self.name),
            ('move_type', 'in', ['out_invoice', 'out_refund'])
        ])
        payments = self.env['account.payment'].search([
            ('invoice_ids', 'in', all_invoices.ids)
        ])
        tree_view = self.env.ref('account.view_account_payment_tree', raise_if_not_found=False)
        form_view = self.env.ref('account.view_account_payment_form', raise_if_not_found=False)

        views = []
        if tree_view:
            views.append((tree_view.id, 'tree'))
        if form_view:
            views.append((form_view.id, 'form'))

        view_mode = 'tree,form' if views else 'form'

        return {
            'name': "Payments",
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'views': views or False,
            'view_mode': view_mode,
            'domain': [('id', 'in', payments.ids)],
            'context': {'default_partner_id': self.partner_id.id},
        }
