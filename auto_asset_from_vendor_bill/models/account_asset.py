from odoo import api, fields, models

class AccountAsset(models.Model):
    _inherit = 'account.asset'

    bill_move_id = fields.Many2one(
        'account.move',
        string='Vendor Bill',
        index=True,
        ondelete='set null',
        help='Bill that created this asset.',
    )
