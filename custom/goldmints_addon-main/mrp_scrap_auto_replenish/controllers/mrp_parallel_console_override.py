import logging
from odoo import http, _
from odoo.http import request
from odoo.tools.float_utils import float_compare
from odoo.addons.mrp_parallel_console.controllers.mrp_parallel_console import MrpParallelConsoleController

_logger = logging.getLogger(__name__)


class MrpParallelConsoleControllerOverride(MrpParallelConsoleController):

    @http.route("/mrp_parallel_console/create_scrap", type="json", auth="user")
    def create_scrap(
        self,
        workorder_id,
        product_id,
        quantity,
        location_id=None,
        scrap_location_id=None,
        reason=None,
        scrap_reason_tag_ids=None,
        lot_id=None,
        lot_name=None,
        workcenter_name=None,
    ):
        # 1. Call the original create_scrap method to handle standard scrap creation and Landed Cost integration
        res = super(MrpParallelConsoleControllerOverride, self).create_scrap(
            workorder_id=workorder_id,
            product_id=product_id,
            quantity=quantity,
            location_id=location_id,
            scrap_location_id=scrap_location_id,
            reason=reason,
            scrap_reason_tag_ids=scrap_reason_tag_ids,
            lot_id=lot_id,
            lot_name=lot_name,
            workcenter_name=workcenter_name,
        )

        # 2. Check if original creation was successful
        if res.get("status") != "success" or "scrap_id" not in res:
            return res

        # 3. Custom Replenishment Logic for Components Only
        try:
            workorder = request.env['mrp.workorder'].browse(workorder_id)
            production = workorder.production_id
            product = request.env['product.product'].browse(product_id)

            # Is this a component? (Not the FG)
            if product.id != production.product_id.id:
                source_loc = production.location_src_id
                
                # Check available stock at the shopfloor location (Pre-Production)
                domain_quants = [
                    ('location_id', '=', source_loc.id),
                    ('product_id', '=', product.id),
                ]
                if lot_id:
                    domain_quants.append(('lot_id', '=', lot_id))
                    
                available_quants = request.env['stock.quant'].search(domain_quants)
                total_available = sum(available_quants.filtered(lambda q: q.quantity > 0).mapped('quantity'))

                # We need to consider what is already reserved for this MO
                # If we have 10 on hand, but 8 are already reserved for this MO, we technically only have 2 "free" to grab.
                # However, for auto-replenish from the same location, if they have physical items there, we just bump the requirement.
                # Odoo will try to reserve the new requirement from the available unreserved stock.
                
                if total_available >= quantity:
                    # Scenario A: Stock is available at shopfloor. We just increase the required qty in the BOM line (move_raw_ids).
                    raw_move = production.move_raw_ids.filtered(lambda m: m.product_id.id == product.id)[:1]
                    if raw_move:
                        # Ensure we don't mess up cost tracking - we just bump the requirement
                        new_qty = raw_move.product_uom_qty + quantity
                        raw_move.sudo().write({'product_uom_qty': new_qty})
                        
                        # Try to reserve the new quantity immediately
                        production.sudo().action_assign()
                        
                        msg = _("✅ Scrap Replenish: Found sufficient '%s' at %s. Increased MO requirement by %s %s automatically.") % (
                            product.display_name, source_loc.display_name, quantity, product.uom_id.name
                        )
                        production.message_post(body=msg)
                        _logger.info("Auto-replenished %s for MO %s (Increased move_raw_ids)", product.display_name, production.name)

                else:
                    # Scenario B: Not enough stock at shopfloor. Create a manual replenishment picking from main stock.
                    warehouse = production.picking_type_id.warehouse_id
                    main_stock_loc = warehouse.lot_stock_id if warehouse else request.env.ref('stock.stock_location_stock', raise_if_not_found=False)
                    
                    if main_stock_loc and main_stock_loc.id != source_loc.id:
                        picking_type = request.env['stock.picking.type'].search([
                            ('code', '=', 'internal'),
                            ('warehouse_id', '=', warehouse.id)
                        ], limit=1)
                        
                        if not picking_type:
                            picking_type = request.env.ref('stock.picking_type_internal', raise_if_not_found=False)

                        if picking_type:
                            picking_vals = {
                                'picking_type_id': picking_type.id,
                                'location_id': main_stock_loc.id,
                                'location_dest_id': source_loc.id,
                                'origin': _("Scrap Replenish for %s") % production.name,
                                'company_id': production.company_id.id,
                                'move_ids': [(0, 0, {
                                    'name': _("Replenish %s") % product.name,
                                    'product_id': product.id,
                                    'product_uom_qty': quantity,
                                    'product_uom': product.uom_id.id,
                                    'location_id': main_stock_loc.id,
                                    'location_dest_id': source_loc.id,
                                    'company_id': production.company_id.id,
                                    'origin': production.name,
                                })]
                            }
                            picking = request.env['stock.picking'].sudo().create(picking_vals)
                            picking.sudo().action_confirm()
                            
                            # Also increase the requirement on the MO so that when the picking arrives, it belongs to this MO
                            raw_move = production.move_raw_ids.filtered(lambda m: m.product_id.id == product.id)[:1]
                            if raw_move:
                                raw_move.sudo().write({'product_uom_qty': raw_move.product_uom_qty + quantity})
                            
                            msg = _("📦 Scrap Replenish: Insufficient stock at shopfloor. Created Internal Transfer <a href=# data-oe-model=stock.picking data-oe-id=%d>%s</a> to replenish %s %s of '%s'.") % (
                                picking.id, picking.name, quantity, product.uom_id.name, product.display_name
                            )
                            production.message_post(body=msg)
                            _logger.info("Created replenishment picking %s for MO %s", picking.name, production.name)

        except Exception as e:
            # We don't want a replenishment failure to break the scrap creation flow.
            _logger.error("Failed to auto-replenish scrap for MO %s: %s", workorder_id, str(e))
            if 'production' in locals():
                production.message_post(body=_("⚠️ Scrap Replenish Failed: %s") % str(e))

        return res
