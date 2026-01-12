# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProductLotTransfer(models.Model):
    _name = "product.lot.transfer"
    _description = "Transfer quantity from Product with in Lot number to another Product or Lot number."

    # name = fields.Char(string="Reference", default="/")
    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default='/')


    effective_date = fields.Datetime(string="Effective Date", help="Date at which the transfer is processed")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ],
        default="draft"
    )

    product_id = fields.Many2one('product.product', string='Source Product', required=True,
                                 domain=[('tracking', '!=', 'none')])
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True,
                                   default=lambda self: self.env['stock.warehouse'].search(
                                       [('company_id', '=', self.env.company.id)], limit=1))
    source_location_id = fields.Many2one('stock.location', string='Source Location', required=True)
    lot_id = fields.Many2one('stock.lot', string='Source Lot', required=True, domain="[('product_id','=',product_id)]")
    qty = fields.Float(string='Quantity', required=True, digits='Product Unit of Measure')
    uom_id = fields.Many2one('uom.uom', string='UoM', related='product_id.uom_id', readonly=True)
    picking_out = fields.Many2one('stock.picking', string='Ref. Out', readonly=True)

    dest_product_id = fields.Many2one('product.product', string='Destination Product', required=True,
                                      domain=[('tracking', '!=', 'none')])
    dest_location_id = fields.Many2one('stock.location', string='Destination Location', required=True)
    dest_lot_id = fields.Many2one('stock.lot', string='Destination Lot', domain="[('product_id','=',dest_product_id)]")
    dest_lot_name = fields.Char(string='New Destination Lot')
    picking_in = fields.Many2one('stock.picking', string='Ref. In', readonly=True)

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('product.lot.transfer') or '/'
        return super(ProductLotTransfer, self).create(vals)

    @api.onchange('product_id')
    def product_id_onchange(self):
        if self.product_id:
            if not self.dest_product_id:
                self.dest_product_id = self.product_id

    @api.onchange('lot_id')
    def lot_id_onchange(self):
        if self.lot_id:
            if self.product_id.tracking == 'serial':
                self.qty = 1
            elif self.qty == 0:
                self.qty = 1

    @api.onchange('source_location_id')
    def source_location_id_onchange(self):
        if self.source_location_id:
            if not self.dest_location_id:
                self.dest_location_id = self.source_location_id

    def _check_available_qty(self):
        self.ensure_one()
        Quant = self.env['stock.quant']
        quants = Quant._gather(self.product_id, self.source_location_id, lot_id=self.lot_id, strict=True)
        available = sum(quants.mapped('quantity')) - sum(quants.mapped('reserved_quantity'))
        if self.qty <= 0:
            raise UserError(_("Quantity must be greater than zero."))
        if available < self.qty - 1e-6:
            raise UserError(
                _("Not enough quantity in source lot.\nAvailable: %s %s") % (available, self.uom_id.display_name))

    def _get_repack_location(self):
        # installed by data file
        loc = self.env.ref('nano_transfer_product_lot.stock_location_repack', raise_if_not_found=False)
        if not loc:
            # fallback: create one under virtual locations
            parent = self.env.ref('stock.stock_location_locations_virtual')
            loc = self.env['stock.location'].create({
                'name': 'Repack',
                'usage': 'internal',
                'location_id': parent.id,
            })
        return loc

    def action_transfer(self):

        self.ensure_one()
        self._check_available_qty()
        try:
            if self.source_location_id.company_id and self.source_location_id.company_id != self.company_id:
                raise UserError(_("Source location belongs to another company."))
            if self.dest_location_id.company_id and self.dest_location_id.company_id != self.company_id:
                raise UserError(_("Destination location belongs to another company."))

            repack_loc = self._get_repack_location()

            # Ensure destination lot
            dest_lot = self.dest_lot_id
            if not dest_lot:

                if not self.dest_lot_name:
                    raise UserError(_("Provide a destination lot or a new lot name."))

                dest_lot = self.env['stock.lot'].search([
                    ('product_id', '=', self.dest_product_id.id),
                    ('name', '=', self.dest_lot_name),
                ])

                if not dest_lot:
                    dest_lot = self.env['stock.lot'].create({
                        'name': self.dest_lot_name,
                        'product_id': self.dest_product_id.id,
                        'company_id': self.company_id.id,
                    })

            # === Check destination stock when product is tracking serial ===
            stock_dest = self.env['stock.quant'].search([
                ('product_id', '=', self.dest_product_id.id),
                ('lot_id', '=', dest_lot.id),
            ])

            if stock_dest:
                if self.dest_product_id.tracking == 'serial':
                    raise UserError(_("The destination lot product is already in stock."))

            # === Check picking_type ===
            picking_type = self.warehouse_id.int_type_id
            if not picking_type:
                raise UserError(_("Warehouse has no Internal Transfer operation type."))

            if repack_loc and dest_lot and picking_type:
                # Internal picking OUT: source product -> Repack
                pick_out = self.picking_out
                if not pick_out:
                    # === New picking_type ===
                    pick_out = self.env['stock.picking'].create({
                        'picking_type_id': picking_type.id,
                        'date_of_transfer': self.effective_date,
                        'location_id': self.source_location_id.id,
                        'location_dest_id': repack_loc.id,
                        'origin': _('Repack OUT: %s -> %s') % (self.lot_id.display_name, dest_lot.display_name),
                    })
                    self.picking_out = pick_out.id
                else:
                    for pick in pick_out:
                        pick.picking_type_id = picking_type.id
                        pick.date_of_transfer = self.effective_date
                        pick.location_id = self.source_location_id.id
                        pick.location_dest_id = repack_loc.id
                        pick.origin = _('Repack OUT: %s -> %s') % (self.lot_id.display_name, dest_lot.display_name)

                move_out = pick_out.move_ids
                if not move_out:
                    move_out = self.env['stock.move'].create({
                        'name': _('Repack OUT %s') % self.product_id.display_name,
                        'product_id': self.product_id.id,
                        'product_uom': self.uom_id.id,
                        'product_uom_qty': self.qty,
                        'picking_id': pick_out.id,
                        'location_id': self.source_location_id.id,
                        'location_dest_id': repack_loc.id,
                    })
                else:
                    for move in move_out:
                        move.name = _('Repack OUT %s') % self.product_id.display_name
                        move.product_id = self.product_id.id
                        move.product_uom = self.uom_id.id
                        move.product_uom_qty = self.qty
                        move.picking_id = pick_out.id
                        move.location_id = self.source_location_id.id
                        move.location_dest_id = repack_loc.id

                move_out._action_confirm()
                move_out._action_assign()

                # set lot on move line and done qty
                for ml in move_out.move_line_ids:
                    ml.lot_id = self.lot_id
                    ml.qty_done = self.qty

                pick_out.button_validate()

                # --- Chack Stock Valuation ---
                vls_remaining = self.env['stock.valuation.layer'].search([
                    ('company_id', '=', self.company_id.id),
                    ('product_id', '=', self.product_id.id),
                    ('lot_id', '=', self.lot_id.id),
                    ('quantity', '>', 0)  # Only consider positive quantities
                ])
                transfer_qty = self.qty
                transfer_unit_cost = vls_remaining.unit_cost
                transfer_values = transfer_qty * transfer_unit_cost

                # --- Stock Valuation Remaining Out ---
                if vls_remaining:
                    for line in vls_remaining:
                        line.remaining_qty -= transfer_qty
                        line.remaining_value -= transfer_values

                # --- Create Stock Valuation Out ---
                svl_vals_out = {
                    'company_id': self.company_id.id,
                    'product_id': self.product_id.id,
                    'stock_move_id': move_out.id,
                    'lot_id': self.lot_id.id,
                    'description': _('Repack OUT %s') % self.product_id.display_name,
                    'unit_cost': transfer_unit_cost,
                    'quantity': -transfer_qty,
                    'value': -transfer_values,
                    'remaining_qty': 0,
                    'remaining_value': 0,
                }
                self.env['stock.valuation.layer'].create(svl_vals_out)

                ####################################################

                # Internal picking IN: dest product from Repack -> dest location
                pick_in = self.picking_in
                if not pick_in:
                    pick_in = self.env['stock.picking'].create({
                        'picking_type_id': picking_type.id,
                        'date_of_transfer': self.effective_date,
                        'location_id': repack_loc.id,
                        'location_dest_id': self.dest_location_id.id,
                        'origin': _('Repack IN: %s') % dest_lot.display_name,
                    })
                    print("pick_in_new:", pick_in)
                    self.picking_in = pick_in.id
                else:
                    for pick in pick_in:
                        pick.picking_type_id = picking_type.id
                        pick.date_of_transfer = self.effective_date
                        pick.location_id = repack_loc.id
                        pick.location_dest_id = self.dest_location_id.id
                        pick.origin = _('Repack IN: %s') % dest_lot.display_name

                move_in = pick_in.move_ids
                if not move_in:
                    move_in = self.env['stock.move'].create({
                        'name': _('Repack IN %s') % self.dest_product_id.display_name,
                        'product_id': self.dest_product_id.id,
                        'product_uom': self.dest_product_id.uom_id.id,
                        'product_uom_qty': self.qty,
                        'quantity': self.qty,
                        'picking_id': pick_in.id,
                        'location_id': repack_loc.id,
                        'location_dest_id': self.dest_location_id.id,
                    })
                else:
                    for move in move_in:
                        move.name = _('Repack IN %s') % self.dest_product_id.display_name
                        move.product_id = self.dest_product_id.id
                        move.product_uom = self.dest_product_id.uom_id.id
                        move.product_uom_qty = self.qty
                        move.quantity = self.qty
                        move.picking_id = pick_in.id
                        move.location_id = repack_loc.id
                        move.location_dest_id = self.dest_location_id.id

                move_in._action_confirm()
                move_in._action_assign()

                # set lot_name or lot_id on move line
                for ml in move_in.move_line_ids:
                    ml.lot_id = dest_lot
                    ml.qty_done = self.qty

                pick_in.button_validate()

                # --- Create Stock Valuation In ---
                svl_vals_in = {
                    'company_id': self.company_id.id,
                    'product_id': self.dest_product_id.id,
                    'stock_move_id': move_in.id,
                    'lot_id': dest_lot.id,
                    'description': _('Repack IN %s') % self.dest_product_id.display_name,
                    'unit_cost': transfer_unit_cost,
                    'quantity': transfer_qty,
                    'value': transfer_values,
                    'remaining_qty': transfer_qty,
                    'remaining_value': transfer_values,
                }
                self.env['stock.valuation.layer'].create(svl_vals_in)
                self.state = 'done'

            else:
                raise UserError("There is incorrect information.\nPlease check the information again.")

        except Exception as e:
            status = str(e)
            raise UserError(_(status))
            # notification_type = 'danger'
            # return {
            #     'type': 'ir.actions.client',
            #     'tag': 'display_notification',
            #     'params': {
            #         'type': notification_type,
            #         'sticky': True,
            #         'message': status,
            #         'title': 'Transfer error!'
            #     }
            # }
