from odoo import models, fields, api
from odoo.exceptions import ValidationError


class PurchaseServiceValidateWizard(models.TransientModel):
    _name = 'purchase.service.validate.wizard'
    _description = 'Validate Service Quantities on Purchase Order'

    order_id = fields.Many2one('purchase.order', required=True, readonly=True)
    line_ids = fields.One2many('purchase.service.validate.wizard.line', 'wizard_id', string='Service Lines')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_id = self.env.context.get('active_id')
        if active_id:
            order = self.env['purchase.order'].browse(active_id)
            res['order_id'] = order.id
            lines_vals = []
            for po_line in order.order_line.filtered(lambda l: l.product_id and l.product_id.type == 'service'):
                lines_vals.append((0, 0, {
                    'order_line_id': po_line.id,
                    'quantity': po_line.qty_received,
                }))
            res['line_ids'] = lines_vals
        return res

    def action_confirm(self):
        self.ensure_one()
        for line in self.line_ids:
            if line.order_line_id:
                current = line.order_line_id.qty_received
                new = line.quantity
                if new < current:
                    raise ValidationError('ไม่สามารถลดจำนวนรับบริการได้')
                line.order_line_id.qty_received = new
        if self.order_id:
            service_lines = self.order_id.order_line.filtered(lambda l: l.product_id and l.product_id.type == 'service')
            if service_lines and all(l.qty_received >= l.product_qty for l in service_lines):
                self.order_id.write({'service_status': 'validated', 'service_validated': True})
        return {'type': 'ir.actions.act_window_close'}


class PurchaseServiceValidateWizardLine(models.TransientModel):
    _name = 'purchase.service.validate.wizard.line'
    _description = 'Service Line Quantity'

    wizard_id = fields.Many2one('purchase.service.validate.wizard', required=True, ondelete='cascade')
    order_line_id = fields.Many2one('purchase.order.line', string='Order Line', readonly=True)
    product_id = fields.Many2one(related='order_line_id.product_id', string='Product', readonly=True)
    uom_id = fields.Many2one(related='order_line_id.product_uom', string='UoM', readonly=True)
    current_qty = fields.Float(related='order_line_id.product_qty', string='Target Qty', readonly=True)
    current_received = fields.Float(related='order_line_id.qty_received', string='Received Qty', readonly=True)
    quantity = fields.Float(string='New Received Qty')
