from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    service_acceptance_ids = fields.One2many(
        'service.acceptance', 'purchase_id', string='Service Acceptances')
    service_acceptance_count = fields.Integer(
        compute='_compute_service_acceptance_count', string='Service Acceptance Count')
    has_service_product = fields.Boolean(
        compute='_compute_has_service_product', store=True)

    @api.depends('order_line.product_id.type', 'order_line.qty_received', 'order_line.product_qty')
    def _compute_has_service_product(self):
        for order in self:
            order.has_service_product = any(
                line.product_id.type == 'service' and line.qty_received < line.product_qty
                for line in order.order_line
            )

    @api.depends('service_acceptance_ids')
    def _compute_service_acceptance_count(self):
        for order in self:
            order.service_acceptance_count = len(order.service_acceptance_ids)

    def action_create_invoice(self):
        """Override to check for service acceptance before creating bill."""
        for order in self:
            if order.has_service_product:
                # Check if there is at least one confirmed (done) service acceptance
                has_confirmed_acceptance = any(
                    acceptance.state == 'done' 
                    for acceptance in order.service_acceptance_ids
                )
                if not has_confirmed_acceptance:
                    raise UserError(_(
                        "You cannot create a bill for this Purchase Order because the service "
                        "has not been accepted yet. Please create and confirm a Service Acceptance first."
                    ))
        return super(PurchaseOrder, self).action_create_invoice()

    def action_view_service_acceptance(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "purchase_service_acceptance.action_service_acceptance")
        action['domain'] = [('purchase_id', '=', self.id)]
        action['context'] = {'default_purchase_id': self.id}
        return action

    def action_create_service_acceptance(self):
        self.ensure_one()
        # Prepare lines
        lines = []
        for line in self.order_line:
            if line.product_id.type == 'service' and line.product_qty > line.qty_received:
                lines.append((0, 0, {
                    'po_line_id': line.id,
                    'name': line.name,
                    'qty_accepted': line.product_qty - line.qty_received,  # Default to remaining qty
                }))

        if not lines:
            # If no service lines or all fully received, maybe still allow creating empty?
            # Or just show warning. Let's allow creating but maybe empty or with all lines.
            # Let's filter for service lines at least.
            for line in self.order_line:
                if line.product_id.type == 'service':
                    lines.append((0, 0, {
                        'po_line_id': line.id,
                        'name': line.name,
                        'qty_accepted': 0.0,
                    }))

        vals = {
            'purchase_id': self.id,
            'acceptance_line_ids': lines
        }
        acceptance = self.env['service.acceptance'].create(vals)

        action = self.env["ir.actions.actions"]._for_xml_id(
            "purchase_service_acceptance.action_service_acceptance")
        action['views'] = [(self.env.ref(
            'purchase_service_acceptance.view_service_acceptance_form').id, 'form')]
        action['res_id'] = acceptance.id
        return action


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.depends('qty_received', 'qty_invoiced', 'product_qty')
    def _compute_qty_invoiced(self):
        super()._compute_qty_invoiced()
        for line in self:
            if line.product_id.type == 'service':
                # Force billing based on received quantity for services
                line.qty_to_invoice = line.qty_received - line.qty_invoiced
