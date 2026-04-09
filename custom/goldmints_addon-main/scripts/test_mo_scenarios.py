# -*- coding: utf-8 -*-
import logging
import random
import traceback

from odoo import SUPERUSER_ID, api, fields

_logger = logging.getLogger(__name__)

LOG_FILE = r'C:\365_project\TheCool18e\Dev\custom\goldmints_addon-main\scripts\error_log.txt'

def log(msg):
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(str(msg) + "\n")
    print(msg)

def run(self):
    """
    Automated MO Scenario Testing Script

    Usage:
    odoo-bin shell -d <db_name>
    >>> from scripts import test_mo_scenarios
    >>> test_mo_scenarios.run(env)
    """
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        f.write("STARTING SCRIPT RUN\n")

    log("STARTING SCRIPT RUN")
    env = self # passed from shell

    # 1. Find all Open MOs (Confirmed or Progress)
    # 1. Find all Open MOs (Confirmed or Progress)
    mos = env['mrp.production'].search([
        ('state', 'in', ['confirmed', 'progress', 'to_close']),
        ('company_id', '=', env.company.id)
    ])

    if not mos:
        log("No open Manufacturing Orders found.")
        # Even if no MOs, we might need to finalize POs
    else:
        log(f"Found {len(mos)} MOs to process...")

    # Define Scenarios
    scenarios = ['normal', 'over_time', 'under_produced', 'scrap']

    success_count = 0

    for mo in mos:
        try:
            scenario = random.choice(scenarios)
            log(f"\nProcessing MO: {mo.name} | Product: {mo.product_id.display_name} | Scenario: {scenario}")

            # 2. Set MPS Week
            # Only if field exists
            if 'mps_week_name' in mo._fields:
                mo.write({'mps_week_name': 'Week 1'})
            else:
                log("  [WARN] mps_week_name field missing!")

            # 3. Check Components and Auto-Purchase
            _ensure_components_availability(env, mo)

            # 4. Process Workorders based on Scenario
            _process_workorders(env, mo, scenario)

            # 5. Finalize MO
            _assign_lots(env, mo) # NEW: Assign lots if needed

            try:
                mo.button_mark_done()
                log(f"  - MO {mo.name} Completed.")
                success_count += 1
            except Exception as e:
                log(f"  [ERROR] Failed to complete MO {mo.name}: {e}")
                log(traceback.format_exc())

            env.cr.commit() # Commit after each MO to save progress
        except Exception as e:
             _logger.error(f"Failed to complete MO {mo.name}: {e}")
             log(f"  [ERROR] Failed to complete MO {mo.name}: {e}")
             log(traceback.format_exc())

    # 6. Process POs and Ensure Scrap
    _process_open_pos(env)
    _ensure_scrap_exists(env, mos)

    log(f"\nFinished. Done MOs: {success_count}/{len(mos)}")

def _assign_lots(env, mo):
    log("  - Assigning Lots...")
    # 1. Finished Good
    if mo.product_id.tracking != 'none' and not mo.lot_producing_id:
        # Create a new lot
        lot_name = f"LOT-{mo.name.replace('/', '').replace(' ', '')}"
        existing_lot = env['stock.lot'].search([
            ('name', '=', lot_name),
            ('product_id', '=', mo.product_id.id),
            ('company_id', '=', mo.company_id.id)
        ], limit=1)

        if not existing_lot:
            lot = env['stock.lot'].create({
                'name': lot_name,
                'product_id': mo.product_id.id,
                'company_id': mo.company_id.id,
            })
        else:
            lot = existing_lot

        mo.lot_producing_id = lot.id
        log(f"    > Assigned FG Lot: {lot.name}")

    # 2. Components
    for move in mo.move_raw_ids:
        if move.state == 'done':
             # Try to fix Lot on Done moves if missing
             if move.product_id.tracking != 'none':
                 for line in move.move_line_ids:
                     if not line.lot_id:
                         # Just try to assign a lot (Might find one or create)
                         lot = env['stock.lot'].search([('product_id','=',move.product_id.id)], limit=1)
                         if not lot:
                             lot = env['stock.lot'].create({'name': 'AUTO-FIX', 'product_id': move.product_id.id, 'company_id': move.company_id.id})
                         try:
                             line.write({'lot_id': lot.id})
                             log(f"    > Fixed Done Move Lot for {move.product_id.name}")
                         except Exception as e:
                             log(f"    [WARN] Failed to patch Done move lot: {e}")
             continue

        if move.product_id.tracking != 'none':
            needs_fix = False
            for line in move.move_line_ids:
                if not line.lot_id:
                    needs_fix = True
                    break

            if not move.move_line_ids and move.state in ['confirmed', 'assigned']:
                needs_fix = True

            if needs_fix:
                log(f"    > Fix needed for {move.product_id.name} (State: {move.state})")

                # 1. Unreserve to clear bad reservation
                if move.state == 'assigned':
                    move._do_unreserve()

                # 2. Find/Create Lot
                lot_name = f"LOT-COMP-{move.product_id.default_code or 'X'}-{random.randint(1000,9999)}"
                lot = env['stock.lot'].search([('product_id', '=', move.product_id.id)], limit=1)
                if not lot:
                    lot = env['stock.lot'].create({
                        'name': lot_name,
                        'product_id': move.product_id.id,
                        'company_id': move.company_id.id,
                    })

                # 3. Ensure Stock Exists with this Lot
                # We simply add stock to the source location to be safe
                env['stock.quant']._update_available_quantity(
                    move.product_id,
                    move.location_id,
                    move.product_uom_qty,
                    lot_id=lot
                )
                log(f"    > Created Stock for {lot.name} at {move.location_id.name}")

                # 4. Re-Assign
                move._action_assign()

                # 5. Verify and Force Lot if needed
                for line in move.move_line_ids:
                    if not line.lot_id:
                        line.lot_id = lot.id

        # FINAL CHECK: Ensure stock exists for whatever lot is assigned (even if previously assigned)
        if move.state not in ['done', 'cancel'] and move.product_id.tracking != 'none':
             # Aggregate per lot
             lot_needs = {}
             for line in move.move_line_ids:
                 if line.lot_id:
                     key = (line.product_id, line.location_id, line.lot_id)
                     if key not in lot_needs:
                         lot_needs[key] = 0.0
                     lot_needs[key] += line.quantity

             for (product, location, lot), total_needed in lot_needs.items():
                 # Check actual stock
                 quants = env['stock.quant'].search([
                     ('product_id', '=', product.id),
                     ('location_id', '=', location.id),
                     ('lot_id', '=', lot.id)
                 ])
                 qty_on_hand = sum(quants.mapped('quantity'))

                 if qty_on_hand < total_needed:
                     shortage = total_needed - qty_on_hand + 10 # Buffer
                     log(f"    > Correction: Found total shortage of {shortage} for {product.name} (Lot {lot.name}). Adding stock...")
                     env['stock.quant']._update_available_quantity(
                         product,
                         location,
                         shortage,
                         lot_id=lot
                     )


def _ensure_components_availability(env, mo):
    """Check stock and purchase missing components."""
    log("  - Checking component availability...")

    missing_components = {} # product: qty_needed

    for move in mo.move_raw_ids:
        if move.state in ['draft', 'waiting', 'partially_available', 'confirmed']:
            # Check availability
            available = move.product_id.qty_available
            needed = move.product_uom_qty
            if available < needed:
                shortage = needed - available
                if move.product_id not in missing_components:
                    missing_components[move.product_id] = 0
                missing_components[move.product_id] += shortage

    if not missing_components:
        log("    > All components available.")
        return

    # Create Purchase Order for missing items
    log(f"    > Found shortages for {len(missing_components)} items. Creating PO...")

    # Simple logic: Find a vendor or create default
    vendor = env['res.partner'].search([('name', '=', 'AutoVendor Logics')], limit=1)
    if not vendor:
        vendor = env['res.partner'].create({'name': 'AutoVendor Logics', 'supplier_rank': 1})

    # FIX: Approve vendor to prevent billing errors
    if 'approval_state' in vendor._fields and vendor.approval_state != 'approved':
         try:
             vendor.write({'approval_state': 'approved'})
             log("    > AutoVendor Logics approved.")
         except Exception as e:
             log(f"    [WARN] Failed to approve vendor: {e}")

    # FIX: Ensure expense account on categories
    try:
        # Removed company_id to prevent error
        expense_acc = env['account.account'].search([('account_type', 'in', ['expense', 'expense_direct_cost'])], limit=1)
    except:
        expense_acc = env['account.account'].search([('code', 'make', '5%')], limit=1) # Fallback

    if expense_acc:
        log(f"    > Found Expense Account: {expense_acc.name}")
        for product in missing_components.keys():
            if not product.categ_id.property_account_expense_categ_id:
                try:
                    product.categ_id.property_account_expense_categ_id = expense_acc.id
                    log(f"    > Fixed Category {product.categ_id.name} Expense Account to {expense_acc.name}")
                except Exception as e:
                    log(f"    [WARN] Failed to set category account: {e}")
    else:
        log("    [WARN] No expense account found to fix categories.")

    po_vals = {
        'partner_id': vendor.id,
        'order_line': [],
        'date_order': fields.Datetime.now(),
    }

    for product, qty in missing_components.items():
        po_vals['order_line'].append((0, 0, {
            'product_id': product.id,
            'product_qty': qty + 10, # Buy a bit extra buffer
            'price_unit': product.standard_price or 10.0, # Fallback price
            'name': product.name,
            'date_planned': fields.Datetime.now(),
            'product_uom': product.uom_id.id,
        }))

    po = env['purchase.order'].create(po_vals)
    po.button_confirm()
    if po.state == 'to approve':
        po.button_approve()
    log(f"    > PO {po.name} Confirmed (State: {po.state}).")

    # Receive Products
    if po.picking_ids:
        picking = po.picking_ids[0]

        # FIX: Receive directly to MO source location to avoid negative stock in sub-locations
        picking.location_dest_id = mo.location_src_id.id

        # Patch for custom validation requirement (Invoice Ref) - Atomic Write
        vals = {}
        if 'invoice_reference' in picking._fields:
             vals['invoice_reference'] = po.name or 'REF-AUTO'
        if 'invoice_date' in picking._fields:
             vals['invoice_date'] = fields.Date.today()
        if vals:
             picking.write(vals)

        for move in picking.move_ids:
            move.location_dest_id = mo.location_src_id.id
            move.quantity = move.product_uom_qty # Set Done Qty

            # FIX: Assign Lot if tracked
            if move.product_id.tracking != 'none':
                # Create a new lot for the received component
                lot_name = f"LOT-PUR-{po.name}-{move.product_id.default_code or 'X'}"
                lot = env['stock.lot'].create({
                    'name': lot_name,
                    'product_id': move.product_id.id,
                    'company_id': move.company_id.id,
                })
                # We need to set the lot on the move line
                # Stock move usually processes via move_line_ids or we can set it on move if simple
                # For tracked products, we should check move_line_ids
                if not move.move_line_ids:
                     # This shouldn't happen if quantity is set?
                     # Actually setting move.quantity (quantity_done) might create lines automatically?
                     # Let's verify. In Odoo 16+, setting quantity creates line.
                     # But setting lot requires accessing the line.
                     pass

                # Ensure line exists and set lot
                if len(move.move_line_ids) == 0:
                     # Create line manually if needed, or rely on Odoo to create it when validating?
                     # Better to create/update line
                     vals = move._prepare_move_line_vals(quantity=0, reserved_quant=False)
                     vals['quantity'] = move.product_uom_qty
                     vals['lot_id'] = lot.id
                     env['stock.move.line'].create(vals)
                else:
                    for line in move.move_line_ids:
                        line.lot_id = lot.id

        picking.button_validate()
        log(f"    > Picking {picking.name} Validated (Stock In) to {mo.location_src_id.name} with Lots.")

    # Assign moves in MO
    mo.action_assign()


def _process_workorders(env, mo, scenario):
    """Process WOs with time tracking/scrap logic."""
    log(f"  - Processing Workorders (Scenario: {scenario})...")

    # If no workorders, check simple production
    if not mo.workorder_ids:
        produced_qty = mo.product_qty
        if scenario == 'under_produced':
            produced_qty = mo.product_qty * 0.8
            log(f"      [Under-produced] Quantity: {produced_qty} (Planned: {mo.product_qty})")

        mo.qty_producing = produced_qty
        return

    for wo in mo.workorder_ids:
        if wo.state in ['done', 'cancel']:
            continue

        log(f"    > WO: {wo.name} ({wo.workcenter_id.name})")

        # Check for blocking WOs
        blocking_wos = env['mrp.workorder'].search([
            ('workcenter_id', '=', wo.workcenter_id.id),
            ('state', '=', 'progress'),
            ('id', '!=', wo.id)
        ])
        for bwo in blocking_wos:
            log(f"      [WARN] Found blocking WO {bwo.name}. Finishing it...")
            try:
                bwo.duration = bwo.duration_expected or 10.0
                bwo.qty_producing = bwo.qty_production
                bwo.button_finish()
            except Exception as e:
                log(f"      [ERROR] Could not finish blocking WO {bwo.name}: {e}")


        # Start WO
        if wo.state != 'progress':
            try:
                wo.button_start()
            except Exception as e:
                log(f"      [WARN] Could not start WO {wo.name}: {e}")
                # Try to proceed anyway if state changed or just force it?
                # If start failed, we might not be able to finish.
                pass

        # Scenario Logic
        duration = wo.duration_expected

        if scenario == 'over_time':
            # 150% - 200% of expected time
            duration = duration * random.uniform(1.5, 2.0)
            log(f"      [Over-time] Duration: {duration:.2f} (Expected: {wo.duration_expected:.2f})")

        elif scenario == 'scrap':
            # Create a Scrap entry for a component
            # Note: Need component lot? Let's assume non-tracked for now
            if mo.move_raw_ids:
                scrap_move = mo.move_raw_ids[0]
                scrap_qty = 1

                log(f"      [Scrap] Scrapping 1 unit of {scrap_move.product_id.name}")
                try:
                    scrap_loc = env['stock.location'].search([('scrap_location', '=', True), ('company_id', 'in', [mo.company_id.id, False])], limit=1)
                    if not scrap_loc:
                         scrap_loc = env['stock.location'].search([('scrap_location', '=', True)], limit=1)
                    if not scrap_loc:
                         # Create one
                         scrap_loc = env['stock.location'].create({
                             'name': 'Auto Scrap',
                             'usage': 'inventory',
                             'scrap_location': True,
                             'company_id': mo.company_id.id,
                         })

                    vals = {
                        'product_id': scrap_move.product_id.id,
                        'scrap_qty': scrap_qty,
                        'product_uom_id': scrap_move.product_uom.id,
                        'production_id': mo.id,
                        'company_id': mo.company_id.id,
                        'location_id': scrap_move.location_id.id, # Consume from components location
                        'scrap_location_id': scrap_loc.id,
                    }
                    scrap = env['stock.scrap'].create(vals)
                    scrap.action_validate()
                except Exception as e:
                    log(f"      [ERROR] Scrap failed: {e}")

        # Record Time
        # Simplest way: update duration on WO directly before marking done
        # Odoo automatically creates productivity lines on done if duration > 0

        wo.duration_expected = duration # Hack to force expected? No.
        # Just use duration variable to set productivity

        # We need to ensure quantity producing is correct
        qty_producing = wo.qty_production

        if scenario == 'under_produced' and wo == mo.workorder_ids[-1]:
             qty_producing = mo.product_qty * 0.8
             log(f"      [Under-produced] Quantity: {qty_producing} (Planned: {mo.product_qty})")

        wo.qty_producing = qty_producing

        # Force duration (simulates real time entry)
        # We must create productivity line manually to set specific duration
        loss_id = env['mrp.workcenter.productivity.loss'].search([('loss_type', '=', 'productive')], limit=1).id
        env['mrp.workcenter.productivity'].create({
            'workorder_id': wo.id,
            'workcenter_id': wo.workcenter_id.id,
            'description': 'Auto Test Log',
            'loss_id': loss_id,
            'date_start': fields.Datetime.now(),
            'date_end': fields.Datetime.now(),
            # Duration field is computed from dates usually, or we can use loss_id for efficiency variance
        })
        # Manually write duration to WO to override computation
        wo.duration = duration

        wo.button_finish()

def use_qty_produced(mo, scenario):
    if scenario == 'under_produced':
        return mo.product_qty * 0.8 # 80%
    return mo.product_qty

def _process_open_pos(env):
    log("\nProcessing Open POs...")

    # 0. Approve Vendor (Late)
    vendor = env['res.partner'].search([('name', '=', 'AutoVendor Logics')], limit=1)
    if vendor and 'approval_state' in vendor._fields and vendor.approval_state != 'approved':
         try:
             vendor.write({'approval_state': 'approved'})
             log("  - AutoVendor Logics approved.")
         except Exception as e:
             log(f"  [WARN] Failed to approve vendor: {e}")

    # 1. Approve stuck POs
    stuck_pos = env['purchase.order'].search([
        ('partner_id.name', '=', 'AutoVendor Logics'),
        ('state', '=', 'to approve')
    ])
    for po in stuck_pos:
        try:
            po.button_approve()
            log(f"  - PO {po.name} Approved.")
        except Exception as e:
            log(f"  [ERROR] Failed to approve PO {po.name}: {e}")

    # 2. Receive pending pickings
    pickings = env['stock.picking'].search([
        ('partner_id.name', '=', 'AutoVendor Logics'),
        ('state', 'in', ['assigned', 'confirmed']),
        ('picking_type_code', '=', 'incoming')
    ])
    for p in pickings:
         try:
             # Patch for validation requirement - Atomic Write
             vals = {}
             if 'invoice_reference' in p._fields and not p.invoice_reference:
                  vals['invoice_reference'] = p.origin or 'REF-AUTO'
             if 'invoice_date' in p._fields and not p.invoice_date:
                  vals['invoice_date'] = fields.Date.today()
             if vals:
                  p.write(vals)

             for move in p.move_ids:
                 move.quantity = move.product_uom_qty

                 # FIX: Assign Lot if tracked
                 if move.product_id.tracking != 'none':
                    lot_name = f"LOT-PUR-AUTO-{move.product_id.default_code}-{random.randint(1000,9999)}"
                    lot = env['stock.lot'].create({
                        'name': lot_name,
                        'product_id': move.product_id.id,
                        'company_id': move.company_id.id,
                    })

                    # Assign lot to lines
                    if not move.move_line_ids:
                         vals = move._prepare_move_line_vals(quantity=0, reserved_quant=False)
                         vals['quantity'] = move.product_uom_qty
                         vals['lot_id'] = lot.id
                         env['stock.move.line'].create(vals)
                    else:
                        for line in move.move_line_ids:
                            line.lot_id = lot.id

             p.button_validate()
             log(f"  - Picking {p.name} Validated.")
         except Exception as e:
             log(f"  [WARN] Picking {p.name} validation failed: {e}")

    # 3. Bill
    # Clean up broken draft bills from previous failures
    draft_bills = env['account.move'].search([
        ('partner_id.name', '=', 'AutoVendor Logics'),
        ('state', '=', 'draft'),
        ('move_type', '=', 'in_invoice')
    ])
    if draft_bills:
        log(f"  - Cleaning {len(draft_bills)} broken draft bills...")
        # (This block now redundant with better fix in create loop, but kept for robustness)
        for bill in draft_bills:
            try:
                 bill.unlink()
            except Exception as e:
                 log(f"    [WARN] Unlink failed for {bill.name or bill.id}: {e}")
                 # Force aggressive unlink
                 try:
                     bill.invoice_line_ids.unlink()
                     bill.line_ids.unlink()
                     bill.unlink()
                     log(f"    > Force unlinked {bill.id}")
                 except Exception as e2:
                     log(f"    [ERROR] Force unlink failed: {e2}")

    # Then create new ones for POs waiting to invoice
    pos = env['purchase.order'].search([
        ('partner_id.name', '=', 'AutoVendor Logics'),
        ('invoice_status', '=', 'to invoice'),
        ('state', 'in', ['purchase', 'done'])
    ])

    if not pos:
        log("No new POs to bill (checked after cleaning).")
    else:
        log(f"Found {len(pos)} POs to bill.")

    for po in pos:
        try:
            # Create Bill
            po.action_create_invoice()

            # Find the new bill
            bills = po.invoice_ids.filtered(lambda x: x.state == 'draft')
            for bill in bills:
                if not bill.ref:
                     bill.ref = po.name
                if not bill.invoice_date:
                     bill.invoice_date = fields.Date.today()

                # Thai Tax Fields FIX - ON ONE2MANY
                for tax_inv in bill.tax_invoice_ids:
                    if not tax_inv.tax_invoice_number:
                        tax_inv.tax_invoice_number = bill.ref or 'TAX-INV-AUTO'
                    if not tax_inv.tax_invoice_date:
                        tax_inv.tax_invoice_date = bill.invoice_date or fields.Date.today()

                bill.action_post()
                log(f"  - PO {po.name} -> Bill {bill.name} Posted.")

        except Exception as e:
            log(f"  [ERROR] Failed to bill PO {po.name}: {e}")
            log(traceback.format_exc())

def _ensure_scrap_exists(env, mos):
    log("\nChecking/Creating High Volume Scrap records...")

    # User Request: "ใส่ lot ที่ scarp ให้ตรงกับที่ผลิตละจำนวน 1000 ทั้งหมดและ validate"
    # -> Create Scrap for MO Product, Lot = Producing Lot, Qty = 1000, Validate.

    if not mos:
        log("No open MOs passed. Searching for recent DONE MOs to apply scrap logic...")
        mos = env['mrp.production'].search([
            ('state', '=', 'done'),
            ('company_id', '=', env.company.id)
        ], order='date_finished desc', limit=50)

    if not mos:
        log("No MOs found to process for scrap.")
        return

    scrap_loc = env['stock.location'].search([('scrap_location', '=', True), ('company_id', 'in', [env.company.id, False])], limit=1)
    if not scrap_loc:
         scrap_loc = env['stock.location'].search([('scrap_location', '=', True)], limit=1)

    if not scrap_loc:
         # Create one
         scrap_loc = env['stock.location'].create({
             'name': 'Auto Scrap',
             'usage': 'inventory',
             'scrap_location': True,
             'company_id': env.company.id,
         })
         log(f"  > Created new Scrap Location: {scrap_loc.name}")
    else:
        log(f"  > Using Scrap Location: {scrap_loc.name}")

    count = 0
    for mo in mos:
        try:
            # Target: Finished Good
            product = mo.product_id
            lot = mo.lot_producing_id
            qty = 1000.0

            # Source Location should be where FG is currently located (usually MO dest location)
            # But scrap usually moves FROM stock.
            # If MO is done, stock is in location_dest_id
            source_loc = mo.location_dest_id

            if not lot and product.tracking != 'none':
                log(f"  [WARN] MO {mo.name} has no producing lot. Skipping.")
                continue

            # Check if already scrapped? (Optional, but user said "ทั้งหมด" - all)
            # We'll just create it.

            vals = {
                'product_id': product.id,
                'scrap_qty': qty,
                'product_uom_id': product.uom_id.id,
                'production_id': mo.id,
                'company_id': mo.company_id.id,
                'location_id': source_loc.id,
                'scrap_location_id': scrap_loc.id,
                'lot_id': lot.id if lot else False,
                'origin': f"Auto-Scrap-{mo.name}"
            }

            # Ensure stock availability?
            # If we scrap 1000 and produced 10, we go negative or fail.
            # Odoo default: allows negative if configuration permits, or warns.
            # We'll try to force simple creation and validate.

            scrap = env['stock.scrap'].create(vals)
            scrap.action_validate()

            log(f"  > Created Scrap {scrap.name} for MO {mo.name} (Lot: {lot.name if lot else 'N/A'}, Qty: {qty})")
            count += 1

        except Exception as e:
            log(f"  [ERROR] Failed to scrap for MO {mo.name}: {e}")
            # log(traceback.format_exc())

    log(f"Finished creating scraps. Total: {count}")
