from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    is_reverse_cheque_entry = fields.Boolean('Is Reverse Cheque Entry?')
    cheque_auto_reconcile_threshold = fields.Float(
        'Cheque Auto Reconcile Threshold',
        default=5.00,
        help='Maximum positive amount difference allowed when auto-matching cheques with bank fees or rounding differences.',
    )
    cheque_rounding_account_id = fields.Many2one(
        'account.account',
        string='Cheque Rounding Account',
        help='Expense or income account used for cheque bank fees and rounding differences during bank statement auto-match.',
    )

    @api.constrains('cheque_auto_reconcile_threshold')
    def _check_cheque_auto_reconcile_threshold(self):
        for company in self:
            if company.cheque_auto_reconcile_threshold < 0:
                raise ValidationError(_("Cheque Auto Reconcile Threshold must be zero or a positive amount."))
