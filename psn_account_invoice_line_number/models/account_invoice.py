from odoo import models, fields, api

class AccountInvoiceLine(models.Model):
    _inherit = 'account.move.line'

    number = fields.Integer(compute='_compute_number', store=True)

    @api.depends('move_id.invoice_line_ids.display_type', 'move_id.invoice_line_ids.sequence')
    def _compute_number(self):
        for invoice in self.mapped('move_id'):
            number = 1
            for line in invoice.invoice_line_ids:
                if line.display_type == 'product':
                    line.number = number
                    number += 1
