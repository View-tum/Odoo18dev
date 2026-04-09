from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ServiceAcceptance(models.Model):
    _name = 'service.acceptance'
    _description = 'Service Acceptance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Reference', required=True,
                       copy=False, readonly=True, default=lambda self: _('New'))
    purchase_id = fields.Many2one('purchase.order', string='Purchase Order',
                                  required=True, readonly=True, states={'draft': [('readonly', False)]})
    partner_id = fields.Many2one('res.partner', string='Vendor',
                                 related='purchase_id.partner_id', store=True, readonly=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today,
                       readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    purchase_count = fields.Integer(
        compute='_compute_purchase_count', string='Purchase Orders')
    acceptance_line_ids = fields.One2many('service.acceptance.line', 'acceptance_id',
                                          string='Acceptance Lines', states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'service.acceptance') or _('New')
        return super(ServiceAcceptance, self).create(vals)

    @api.depends("acceptance_line_ids")
    def _compute_purchase_count(self):
        for rec in self:
            rec.purchase_count = len(rec.mapped(
                "acceptance_line_ids.po_line_id"))

    def action_view_purchase_order(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "purchase.purchase_rfq")
        orders = self.mapped("acceptance_line_ids.po_line_id.order_id")
        if len(orders) > 1:
            action["domain"] = [("id", "in", orders.ids)]
        elif orders:
            action["views"] = [
                (self.env.ref("purchase.purchase_order_form").id, "form")
            ]
            action["res_id"] = orders.id
        return action

    def action_confirm(self):
        for acceptance in self:
            if not acceptance.acceptance_line_ids:
                raise UserError(_('Please add some lines to accept.'))

            for line in acceptance.acceptance_line_ids:
                if line.qty_accepted <= 0:
                    continue
                # Update PO Line Received Qty
                line.po_line_id.qty_received += line.qty_accepted

            acceptance.write({'state': 'done'})
        return True

    def action_cancel(self):
        for acceptance in self:
            if acceptance.state == 'done':
                # Revert the qty received on PO
                for line in acceptance.acceptance_line_ids:
                    line.po_line_id.qty_received -= line.qty_accepted
            acceptance.write({'state': 'cancel'})
        return True

    def action_draft(self):
        self.write({'state': 'draft'})


class ServiceAcceptanceLine(models.Model):
    _name = 'service.acceptance.line'
    _description = 'Service Acceptance Line'

    acceptance_id = fields.Many2one(
        'service.acceptance', string='Acceptance', required=True, ondelete='cascade')
    po_line_id = fields.Many2one(
        'purchase.order.line', string='Purchase Order Line', required=True)
    product_id = fields.Many2one(
        'product.product', string='Product', related='po_line_id.product_id', readonly=True)
    name = fields.Text(string='Description', required=True)
    qty_to_accept = fields.Float(
        string='To Accept', compute='_compute_qty_to_accept', store=True)
    qty_accepted = fields.Float(
        string='Accepted Qty', required=True, default=0.0)
    product_uom = fields.Many2one(
        'uom.uom', string='Unit of Measure', related='po_line_id.product_uom', readonly=True)

    @api.depends('po_line_id.product_qty', 'po_line_id.qty_received')
    def _compute_qty_to_accept(self):
        for line in self:
            line.qty_to_accept = max(
                0.0, line.po_line_id.product_qty - line.po_line_id.qty_received)
