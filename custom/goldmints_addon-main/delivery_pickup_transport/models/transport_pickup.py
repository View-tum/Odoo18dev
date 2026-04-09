
# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_STATES = [
    ("draft", "Draft"),
    ("done", "Done")
]


class TransportPickup(models.Model):
    _name = 'transport.pickup'
    _description = 'Transporter Pick Up from Our Warehouse (A4 PDF Form)'
    _order = 'id desc'

    name = fields.Char(
        string='Document No.',
        required=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('transport.pickup') or _('New'),
        help=   "(365 custom) Document number for this pickup note. Automatically generated if left empty."
    )
    date = fields.Date(
        string='Date',
        default=fields.Date.context_today,
        required=True,
        help="(365 custom) The date this pickup document was created."
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
        help="(365 custom) The company this record belongs to."
    )

    carrier_id = fields.Many2one(
        'res.partner',
        string='Carrier/Transporter',
        help="(365 custom) The carrier or transporter company picking up the goods."
    )
    responsible_id = fields.Many2one(
        'hr.employee',
        string='Responsible',
        help="(365 custom) The internal employee responsible for preparing the goods for pickup."
    )
    driver_name = fields.Char(
        string='Driver Name',
        help="(365 custom) Name of the driver picking up the goods."
    )
    driver_phone = fields.Char(
        string='Driver Phone',
        help="(365 custom) Phone number of the driver."
    )
    vehicle_no = fields.Char(
        string='Vehicle No.',
        help="(365 custom) License plate number of the vehicle."
    )
    route = fields.Char(
        string='Route / Destination',
        help="(365 custom) The route or destination for this transport trip."
    )
    trip_count = fields.Integer(
        string='Trip No.',
        default=1,
        help="(365 custom) The trip number for the day."
    )

    total_boxes = fields.Integer(
        string='Total Boxes',
        compute='_compute_totals',
        store=True,
        help="(365 custom) Total number of boxes for this pickup, calculated automatically from the item lines."
    )
    line_ids = fields.One2many(
        'transport.pickup.line',
        'order_id',
        string='Items',
        help="(365 custom) All product items included in this pickup."
    )
    
    consignee_id = fields.Many2one(
        'res.partner',
        string='Receiver (To Warehouse)',
        help="(365 custom) The destination warehouse that will receive the goods."
    )
    consignee_contact = fields.Char(
        string='Contact Name',
        help="(365 custom) Name of the contact person at the destination warehouse."
    )
    consignee_phone = fields.Char(
        string='Phone',
        help="(365 custom) Phone number for the destination contact."
    )
    consignee_address = fields.Char(
        string='Destination Address',
        help="(365 custom) The address of the destination warehouse."
    )
    license_plate_no = fields.Char(string='License Plate No.')
    
        
    state = fields.Selection(
        selection=_STATES,
        string="Status",
        index=True,
        tracking=True,
        required=True,
        copy=False,
        default="draft",
        help="(365 custom) Status of the pickup note. 'Draft' = In progress, 'Done' = Pickup completed."
    )
    
    is_editable = fields.Boolean(
        compute="_compute_is_editable",
        readonly=True,
        help="(365 custom) Technical field indicating if the document can be edited (i.e., not in 'Done' state)."
    )
    
    @api.depends("state")
    def _compute_is_editable(self):
        for rec in self:
            if rec.state in ("done"):
                rec.is_editable = False
            else:
                rec.is_editable = True
    
    def button_done(self):
        for rec in self:
            # if no line items, block state change
            if not rec.line_ids:
                raise UserError(_("Please add at least one item line before marking as Done."))
            else:
                return self.write({"state": "done"})

    @api.depends('responsible_id','line_ids.product_qty')
    def _compute_totals(self):
        for rec in self:
            rec.total_boxes = int(sum(rec.line_ids.mapped('product_qty')))


class TransportPickupLine(models.Model):
    _name = 'transport.pickup.line'
    _description = 'Transporter Pickup Lines'
    _order = 'id'
    
    @api.model
    def _default_uom_id(self):
        return self.env['uom.uom'].search([('name', '=', 'Box')], limit=1)

    sequence = fields.Integer(
        default=10,
        help="(365 custom) Display order for the line item."
    )
    order_id = fields.Many2one(
        'transport.pickup',
        ondelete='cascade',
        help="(365 custom) Technical field linking to the parent transport pickup document."
    )
    product_id = fields.Many2one(
        'product.product',
        required=True,
        help="(365 custom) The product being picked up."
    )
    product_qty = fields.Float(
        'Quantity',
        help="(365 custom) Total quantity of the product for this line."
    )
    uom_id = fields.Many2one(
        'uom.uom',
        required=True,
        default=_default_uom_id,
        help="(365 custom) Unit of Measure for the quantity (e.g., Box)."
    )
    product_description = fields.Char(
        string='Description',
        help="(365 custom) Additional description for the product on this line."
    )
    pack_size = fields.Char(
        string='Pack/Size',
        help="(365 custom) The packing size or dimension of the product."
    )
    qty_boxes = fields.Integer(
        string='Boxes',
        default=1,
        help="(365 custom) The number of boxes for this specific product line."
    )
