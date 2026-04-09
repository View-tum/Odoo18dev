# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

_STATES = [
    ("draft", "Draft"),
    ("done", "Done")
]

class ExportShipment(models.Model):
    _name = 'export.shipment'
    _description = 'Export Shipment'
    _order = 'id desc'

    name = fields.Char(
        string='Document No.',
        required=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('export.shipment') or _('New'),
        help="(365 custom) Document number for this export shipment. Automatically generated if left empty."
    )
    date = fields.Date(
        string='Date',
        default=fields.Date.context_today,
        required=True,
        help="(365 custom) The date this export shipment document was created."
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
        help="(365 custom) The company this record belongs to."
    )
    order_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        required=True,
        help="(365 custom) The sale order linked to this export shipment."
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        related='order_id.partner_id',
        store=True,
        readonly=True,
        help="(365 custom) Customer from the selected sale order."
    )
    line_ids = fields.One2many(
        'export.shipment.line',
        'shipment_id',
        string='Order Lines',
        help="(365 custom) Sale order lines copied into this export shipment."
    )
    state = fields.Selection(
        selection=_STATES,
        string="Status",
        index=True,
        tracking=True,
        required=True,
        copy=False,
        default="draft",
        help="(365 custom) Status of the export shipment. 'Draft' = In progress, 'Done' = Completed."
    )
    total_boxes = fields.Integer(
        string='Total Boxes',
        compute='_compute_totals',
        store=True,
        help="(365 custom) Total number of boxes for this shipment, calculated automatically from the item lines."
    )
    is_editable = fields.Boolean(
        compute="_compute_is_editable",
        readonly=True,
        help="(365 custom) Technical field indicating if the document can be edited (i.e., not in 'Done' state)."
    )

    @api.onchange('order_id')
    def _onchange_order_id(self):
        for rec in self:
            if not rec.order_id:
                rec.line_ids = [(5, 0, 0)]
                continue
            
            box_uom = self.env['uom.uom'].search([('name', '=', 'Box')], limit=1)
            
            lines = []
            for line in rec.order_id.order_line.filtered(lambda l: not l.display_type):
                lines.append((0, 0, {
                    'sale_line_id': line.id,
                    'product_id': line.product_id.id,
                    'name': line.name,
                    'product_qty': line.product_uom_qty,
                    # Fallback to product_uom if Box is not found in the system
                    'uom_id': box_uom.id if box_uom else line.product_uom.id,
                }))
            rec.line_ids = [(5, 0, 0)] + lines

    @api.depends('line_ids.product_qty')
    def _compute_totals(self):
        for rec in self:
            rec.total_boxes = int(sum(rec.line_ids.mapped('product_qty')))

    @api.depends("state")
    def _compute_is_editable(self):
        for rec in self:
            if rec.state in ("done"):
                rec.is_editable = False
            else:
                rec.is_editable = True

    def button_done(self):
        for rec in self:
            return self.write({"state": "done"})


class ExportShipmentLine(models.Model):
    _name = 'export.shipment.line'
    _description = 'Export Shipment Line'
    _order = 'id'

    shipment_id = fields.Many2one(
        'export.shipment',
        ondelete='cascade',
        help="(365 custom) Technical field linking to the parent export shipment."
    )
    sale_line_id = fields.Many2one(
        'sale.order.line',
        string='Sale Order Line',
        readonly=True,
        help="(365 custom) Source sale order line."
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        help="(365 custom) Product from the sale order line."
    )
    name = fields.Char(
        string='Description',
        help="(365 custom) Description from the sale order line."
    )
    product_qty = fields.Float(
        string='Quantity',
        help="(365 custom) Quantity from the sale order line."
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        help="(365 custom) Unit of measure from the sale order line."
    )
    mfg = fields.Date(
        string='MFG',
        help="(365 custom) Manufacturing Date"
    )
    exp = fields.Date(
        string='EXP',
        help="(365 custom) Expiry Date"
    )
    lot = fields.Char(
        string='Lot',
        help="(365 custom) Lot Number (Text)"
    )
    image = fields.Image(
        string='Image',
        help="(365 custom) Optional picture for this export shipment line."
    )
