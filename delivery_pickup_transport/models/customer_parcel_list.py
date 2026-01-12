from odoo import api, fields, models, _
from odoo.exceptions import UserError


_STATES = [
    ("draft", "Draft"),
    ("done", "Done")
]

class CustomerParcelList(models.Model):
    _name = 'customer.parcel.list'
    _description = 'Customer Parcel List'
    _order = 'id desc'
    
    name = fields.Char(
        string='Document No.',
        required=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('customer.parcel.list') or _('New'),
        help="(365 custom) Document number for this parcel list. Automatically generated if left empty."
    )
    date = fields.Date(
        string='Date',
        default=fields.Date.context_today,
        required=True,
        help="(365 custom) The date this document was created"
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
        help="(365 custom) The logistics partner or person responsible for transporting the parcels."
    )
    responsible_id = fields.Many2one(
        'hr.employee',
        string='Responsible',
        help="(365 custom) The internal employee responsible for this list."
    )
    line_ids = fields.One2many(
        'customer.parcel.list.line',
        'list_id',
        string='Items',
        help="(365 custom) Details of the individual parcel items included in this list."
    )
    state = fields.Selection(
        selection=_STATES,
        string="Status",
        index=True,
        tracking=True,
        required=True,
        copy=False,
        default="draft",
        help="(365 custom) Status of the parcel list. 'Draft' = In progress, 'Done' = Completed."
    )

    is_editable = fields.Boolean(
        compute="_compute_is_editable",
        readonly=True,
        help="(365 custom) Technical field indicating if the document can be edited (i.e., not in 'Done' state)."
    )

    total_boxes = fields.Integer(string='Total Boxes', compute='_compute_totals', store=True)
    
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
            # if no line items, block state change
            if not rec.line_ids:
                raise UserError(_("Please add at least one item line before marking as Done."))
            else:
                return self.write({"state": "done"})
    
    
class CustomerparcelListLine(models.Model):
    _name = 'customer.parcel.list.line' 
    _description = 'Customer parcel List'
    _order = 'id'
    
    @api.model
    def _default_uom_id(self):
        return self.env['uom.uom'].search([('name', '=', 'Box')], limit=1)
    
    customer_id = fields.Many2one(
        'res.partner',
        string='Customer',
        help="(365 custom)The customer (recipient) for this specific parcel."
    )
    product_qty = fields.Float(
        'Quantity',
        help="(365 custom) The quantity of parcels for this customer."
    )
    uom_id = fields.Many2one(
        'uom.uom',
        required=True,
        default=_default_uom_id,
        help="(365 custom) Unit of Measure for the quantity (e.g., Box, Pcs)."
    )
    list_id = fields.Many2one(
        'customer.parcel.list',
        ondelete='cascade',
        help="(365 custom) Technical field linking to the parent Customer Parcel List."
    )
    note = fields.Char(
        string='Note',
        help="(365 custom) Shipping mark or additional note."
    )