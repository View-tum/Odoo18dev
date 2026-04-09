from odoo import models, fields, api

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    sale_note = fields.Text(
        string='Sale Note',
        compute='_compute_sale_info',
        store=True,
        readonly=True
    )
    internal_note = fields.Text(
        string='Internal Note',
        compute='_compute_sale_info',
        store=True,
        readonly=True
    )

    @api.depends('procurement_group_id.sale_id', 'move_dest_ids.sale_line_id.order_id')
    def _compute_sale_info(self):
        for mo in self:
            sale_orders = self.env['sale.order']
            
            # 1. Check procurement group (Common for MTO/Replenish)
            if mo.procurement_group_id.sale_id:
                sale_orders |= mo.procurement_group_id.sale_id
            
            # 2. Check destination moves (linked SO lines)
            if mo.move_dest_ids:
                sale_orders |= mo.move_dest_ids.mapped('sale_line_id.order_id')

            if sale_orders:
                mo.sale_note = "\n".join(filter(None, sale_orders.mapped('sale_note')))
                mo.internal_note = "\n".join(filter(None, sale_orders.mapped('internal_note')))
            else:
                mo.sale_note = False
                mo.internal_note = False
