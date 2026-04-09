from odoo import models, fields

class ChequeInboundOutbound(models.Model):
    _inherit = 'cheque.inbound.outbound'

    partner_user_id = fields.Many2one(
        comodel_name='res.users',
        related='pay_partner_id.user_id',
        string='Salesperson',
        store=True
    )
    partner_salesregion_id = fields.Many2one(
        comodel_name='delivery.sales.region',
        related='pay_partner_id.salesregion_id',
        string='Sales Region',
        store=True
    )
    partner_subregion_id = fields.Many2one(
        comodel_name='delivery.sub.region',
        related='pay_partner_id.subregion_id',
        string='Subregion',
        store=True
    )