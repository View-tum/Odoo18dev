from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    proforma_invoice_no = fields.Char(
        string="Proforma Invoice No.",
        copy=False,
        help="Automated or manual reference for the Proforma Invoice number."
    )

    reference_pi = fields.Char(
        string="Reference PI",
        help="Additional reference for the Proforma Invoice."
    )

    partner_credit_balance = fields.Monetary(
        string="Credit Balance",
        currency_field='currency_id',
        help="Credit balance for reporting purposes."
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('proforma_invoice_no'):
                user_id = vals.get('user_id') or self.env.uid
                user = self.env['res.users'].browse(user_id)

                # Simplified: only check user access rights
                if user.use_proforma_sequence or self.env.user.use_proforma_sequence:
                    company_id = vals.get('company_id') or self.env.company.id
                    company = self.env['res.company'].browse(company_id)
                    seq = company.proforma_sequence_id or self.env['ir.sequence'].search([
                        ('code', '=', 'sale.order.proforma'),
                        ('company_id', 'in', [company.id, False])
                    ], limit=1, order='company_id desc')

                    if seq:
                        vals['proforma_invoice_no'] = seq.next_by_id()

        return super().create(vals_list)

    def action_generate_proforma_no(self):
        for order in self:
            if not order.proforma_invoice_no:
                if order.user_id.use_proforma_sequence or self.env.user.use_proforma_sequence:
                    seq = order.company_id.proforma_sequence_id or self.env['ir.sequence'].search([
                        ('code', '=', 'sale.order.proforma'),
                        ('company_id', 'in', [order.company_id.id, False])
                    ], limit=1, order='company_id desc')
                    if seq:
                        order.proforma_invoice_no = seq.next_by_id()
        return True


