from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    proforma_sequence_id = fields.Many2one(
        'ir.sequence',
        string="Proforma Sequence",
        domain="[('code', '=', 'sale.order.proforma')]",
        default=lambda self: self.env.ref('sale_extra_info.seq_sale_order_proforma', raise_if_not_found=False)
    )
