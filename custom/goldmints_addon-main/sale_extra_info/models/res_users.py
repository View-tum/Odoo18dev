from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    use_proforma_sequence = fields.Boolean(
        string="Use Proforma Sequence",
        help="If checked, this user can trigger Proforma Invoice number generation on Sale Orders."
    )
