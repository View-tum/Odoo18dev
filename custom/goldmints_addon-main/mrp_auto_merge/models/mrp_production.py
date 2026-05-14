import logging
import re
from datetime import timedelta, datetime, date

from markupsafe import Markup
from odoo import _, api, fields, models
from odoo.tools import html_escape
from odoo.tools.float_utils import float_round
from odoo.tools.misc import topological_sort

_logger = logging.getLogger(__name__)

SALE_ORDER_NAME_RE = re.compile(r"\bSO[A-Z]*-\d+\b|\bS\d{4,}\b")
MO_NAME_RE = re.compile(r"\b(?:GMP|M-WH|WH)/MO[A-Z]*/\d+\b")


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    root_mo_id = fields.Many2one(
        'mrp.production',
        string="Root MO",
        compute='_compute_root_mo_id',
        store=True,
        help="The top-level MO in the production chain (FG level)",
    )

    source_sale_order_id = fields.Many2one(
        'sale.order',
        string="Source Sales Order",
        compute='_compute_source_sale_order_id',
        store=True,
        index=True,
        help="The original Sales Order that triggered this production chain (MTO)."
    )

    is_mto = fields.Boolean(
        string="MTO Order",
        compute='_compute_is_mto',
        store=True,
        index=True,
        help="True if this order is linked to a Sales Order."
    )

    @api.depends('origin', 'procurement_group_id.sale_id')
    def _compute_root_mo_id(self):
        mo_cache = {}
        for mo in self:
            mo.root_mo_id = mo._find_root_mo(mo_cache=mo_cache)

    @api.depends('origin', 'procurement_group_id.sale_id')
    def _compute_source_sale_order_id(self):
        mo_cache = {}
        so_cache = {}
        for mo in self:
            mo.source_sale_order_id = mo._find_source_so(mo_cache=mo_cache, so_cache=so_cache)

    @api.depends('source_sale_order_id')
    def _compute_is_mto(self):
        for mo in self:
            mo.is_mto = bool(mo.source_sale_order_id)

    def _split_origin_refs(self, origin):
        return [part.strip() for part in (origin or '').split(',') if part.strip()]

    def _find_sale_order_from_origin_text(self, origin, so_cache=None):
        SaleOrder = self.env['sale.order']
        for so_name in SALE_ORDER_NAME_RE.findall(origin or ''):
            if so_cache is not None and so_name in so_cache:
                sale = so_cache[so_name]
            else:
                sale = SaleOrder.search([('name', '=', so_name)], limit=1)
                if so_cache is not None:
                    so_cache[so_name] = sale
            if sale:
                return sale
        return SaleOrder

    def _find_parent_mos_from_origin_text(self, origin):
        names = []
        for part in self._split_origin_refs(origin):
            names.extend(MO_NAME_RE.findall(part))
        if not names:
            names = MO_NAME_RE.findall(origin or '')
        if not names:
            return self.env['mrp.production']
        return self.search([('name', 'in', list(dict.fromkeys(names)))])

    def _default_bom_for_product(self, product, company_id=False):
        if not product:
            return self.env['mrp.bom']
        company_id = company_id or self.env.company.id
        return self.env['mrp.bom']._bom_find(
            products=product,
            company_id=company_id,
        ).get(product)

    def _source_sale_order_id_from_create_vals(self, vals):
        if vals.get('source_sale_order_id'):
            return vals['source_sale_order_id']

        group = vals.get('procurement_group_id')
        if isinstance(group, int):
            group = self.env['procurement.group'].browse(group)
        if group and group.exists() and group.sale_id:
            return group.sale_id.id

        origin = vals.get('origin')
        sale = self._find_sale_order_from_origin_text(origin)
        if sale:
            return sale.id

        for parent in self._find_parent_mos_from_origin_text(origin):
            sale = parent._find_source_so()
            if sale:
                return sale.id
        return False

    def _apply_default_bom_to_create_vals(self, vals):
        if vals.get('bom_id') or not vals.get('product_id'):
            return
        product = self.env['product.product'].browse(vals['product_id'])
        bom = self._default_bom_for_product(
            product,
            vals.get('company_id') or self.env.company.id,
        )
        if bom:
            vals['bom_id'] = bom.id

    def _is_auto_merge_protected_create_vals(self, vals):
        """Block ambiguous MTO merges, but allow SO-scoped MTO merges.

        MTO productions with a source SO can be safely merged with productions
        from the same SO. MTO productions without that source link are not safe
        to merge because the demand chain cannot be traced back reliably.
        """
        return bool(vals.get('is_mto') and not vals.get('source_sale_order_id'))

    def _is_backorder_create_vals(self, vals):
        """Standard MRP backorders must stay as separate -001/-002 records."""
        return bool(vals.get('backorder_sequence'))

    @api.depends(
        'procurement_group_id',
        'procurement_group_id.stock_move_ids.group_id',
        'move_raw_ids.picking_id',
        'move_raw_ids.move_orig_ids.picking_id',
        'move_finished_ids.picking_id',
        'move_finished_ids.move_dest_ids.picking_id',
    )
    def _compute_picking_ids(self):
        super()._compute_picking_ids()
        for production in self:
            direct_pickings = (
                production.move_raw_ids.picking_id
                | production.move_raw_ids.move_orig_ids.picking_id
                | production.move_finished_ids.picking_id
                | production.move_finished_ids.move_dest_ids.picking_id
            ).filtered(lambda picking: picking.state != 'cancel')
            if direct_pickings:
                production.picking_ids = (production.picking_ids | direct_pickings).sorted()
                production.delivery_count = len(production.picking_ids)

    def _find_root_mo(self, mo_cache=None):
        self.ensure_one()
        if mo_cache is not None and self in mo_cache:
            return mo_cache[self]

        if not self.origin:
            res = self
        else:
            origin_parts = self._split_origin_refs(self.origin)
            if not origin_parts:
                res = self
            else:
                first_origin = origin_parts[0]
                # Skip SO origins when looking for Root MO, we want the highest MO
                if self._find_sale_order_from_origin_text(first_origin):
                    res = self
                elif MO_NAME_RE.search(first_origin):
                    parent_mo = self.search(
                        [('name', '=', MO_NAME_RE.search(first_origin).group(0))],
                        limit=1,
                    )
                    res = parent_mo._find_root_mo(mo_cache=mo_cache) if parent_mo else self
                else:
                    res = self

        if mo_cache is not None:
            mo_cache[self] = res
        return res

    def _find_source_so(self, mo_cache=None, so_cache=None):
        self.ensure_one()
        if mo_cache is not None and self in mo_cache:
            return mo_cache[self]

        # 1. Direct Link (Standard Odoo MTO)
        so = self.procurement_group_id.sale_id or (hasattr(self, 'sale_line_id') and self.sale_line_id.order_id)
        if not so and self.origin:
            # 2. Check Origin. Origins can be "SOB-263077",
            # "FG-... - SOB-263077", or comma-separated parent MO names.
            so = self._find_sale_order_from_origin_text(self.origin, so_cache=so_cache)

            # 3. Traversal (Check parent MOs by name)
            if not so:
                for parent in self._find_parent_mos_from_origin_text(self.origin):
                    if parent and parent != self:
                        so = parent._find_source_so(
                            mo_cache=mo_cache,
                            so_cache=so_cache,
                        )
                        if so:
                            break

        if mo_cache is not None:
            mo_cache[self] = so
        return so or self.env['sale.order']

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._apply_default_bom_to_create_vals(vals)
            so_id = self._source_sale_order_id_from_create_vals(vals)
            if so_id and not vals.get('source_sale_order_id'):
                vals['source_sale_order_id'] = so_id

        if any(self._is_auto_merge_protected_create_vals(vals) for vals in vals_list):
            return super().create(vals_list)

        if any(self._is_backorder_create_vals(vals) for vals in vals_list):
            return super().create(vals_list)

        if self.env.context.get('skip_auto_merge'):
            return super().create(vals_list)

        params = self.env['ir.config_parameter'].sudo()
        enabled = params.get_param('mrp_auto_merge.enabled', 'True') == 'True'
        if not enabled:
            return super().create(vals_list)

        date_range = int(params.get_param('mrp_auto_merge.date_range', '7'))

        # 1. Identify Batch-Level Merges and Database-Level Merges
        # result_map maps original index in vals_list to (Record, Status)
        # where Status can be 'updated' or 'to_create'
        result_map = {}
        batch_leaders = {} # key -> first index in vals_list

        def _get_so_id_from_vals(v):
            so_id = v.get('source_sale_order_id')
            if so_id:
                return so_id
            pg_id = v.get('procurement_group_id')
            if pg_id:
                pg = self.env['procurement.group'].browse(pg_id)
                if pg.sale_id:
                    return pg.sale_id.id
            origin = v.get('origin')
            if origin:
                for part in (origin or '').split(','):
                    part = part.strip()
                    if part.startswith('SO'):
                        so = self.env['sale.order'].search([('name', '=', part)], limit=1)
                        if so:
                            return so.id
            return False

        # We need a predictable key for grouping
        def get_merge_key(v):
            p_id = v.get('product_id')
            b_id = v.get('bom_id')
            c_id = v.get('company_id') or self.env.company.id
            pt_id = v.get('picking_type_id') or self.env.context.get('default_picking_type_id')
            
            so_id = _get_so_id_from_vals(v)
            if so_id:
                return (p_id, b_id, c_id, so_id)
            # Bucket date into a rough start date for fuzzy matching
            d_str = v.get('date_start')
            d_date = None
            if d_str:
                if isinstance(d_str, datetime):
                    d_date = d_str.date()
                elif isinstance(d_str, date):
                    d_date = d_str
                else:
                    try:
                        d_date = fields.Datetime.to_datetime(d_str).date()
                    except Exception:
                        try:
                            d_date = fields.Date.to_date(d_str)
                        except Exception:
                            pass
            if not d_date:
                d_date = fields.Date.today()
            return (p_id, b_id, c_id, pt_id, so_id, d_date)

        # First Pass: Intra-batch Consolidation
        for i, vals in enumerate(vals_list):
            key = get_merge_key(vals)
            if key in batch_leaders:
                leader_idx = batch_leaders[key]
                # Merge this vals into the leader vals
                self._merge_vals_into_vals(vals_list[leader_idx], vals)
                result_map[i] = ('merged_with_leader', leader_idx)
            else:
                batch_leaders[key] = i

        # Second Pass: Database-Level Pre-emptive Check
        # to_create_list stores (original_index, vals) for items that MUST be created
        to_create_list = []
        created_records = {} # leader_idx -> Record

        for i, vals in enumerate(vals_list):
            if i in result_map: # Already handled (merged into leader)
                continue

            # This is a Batch Leader. Check if it can merge with an existing DB record
            target = self._find_preemptive_target(vals, date_range)
            if target:
                target._merge_vals_into(vals)
                created_records[i] = target
                result_map[i] = ('updated_db', target)
            else:
                to_create_list.append((i, vals))

        # 2. Perform Batch Creation for non-merged items
        if to_create_list:
            raw_vals = [x[1] for x in to_create_list]
            print(f"raw_vals before create: {raw_vals}")
            new_records = super().create(raw_vals)
            for (original_idx, _unused_val), record in zip(to_create_list, new_records):
                merged_record = record._try_merge_with_existing(date_range=date_range) or record
                created_records[original_idx] = merged_record
                result_map[original_idx] = ('newly_created', merged_record)

        # 3. Final Construction of the Return Recordset (maintain length & order)
        final_list = []
        for i in range(len(vals_list)):
            status, info = result_map[i]
            if status == 'merged_with_leader':
                final_list.append(created_records[info])
            else:
                final_list.append(info if status == 'updated_db' else created_records[i])

        return self.env['mrp.production'].concat(*final_list)

    def _merge_vals_into_vals(self, master_vals, add_vals):
        """Merge values of one dict into another (Intra-batch)."""
        master_vals['product_qty'] = master_vals.get('product_qty', 0.0) + add_vals.get('product_qty', 0.0)

        # Merge Origin
        o1 = master_vals.get('origin', '') or ''
        o2 = add_vals.get('origin', '') or ''
        origins = [x.strip() for x in o1.split(',') if x.strip()]
        if o2 and o2 not in origins:
            origins.append(o2)
        master_vals['origin'] = ', '.join(origins) if origins else False

        # Merge Source Sale Order
        if add_vals.get('source_sale_order_id') and not master_vals.get('source_sale_order_id'):
            master_vals['source_sale_order_id'] = add_vals.get('source_sale_order_id')

        master_vals['move_dest_ids'] = self._merge_move_dest_commands(
            master_vals.get('move_dest_ids'),
            add_vals.get('move_dest_ids'),
        )

    def _extract_move_dest_command_ids(self, commands):
        dest_ids = []
        for command in commands or []:
            if not isinstance(command, (list, tuple)) or not command:
                continue
            if command[0] == 4 and len(command) >= 2:
                dest_ids.append(command[1])
            elif command[0] == 6 and len(command) >= 3:
                dest_ids.extend(command[2] or [])
        return list(dict.fromkeys(dest_ids))

    def _merge_move_dest_commands(self, master_commands, add_commands):
        """Preserve downstream demand links when several MO vals are merged."""
        merged_ids = self._extract_move_dest_command_ids(master_commands)
        for dest_id in self._extract_move_dest_command_ids(add_commands):
            if dest_id not in merged_ids:
                merged_ids.append(dest_id)
        return [(6, 0, merged_ids)] if merged_ids else master_commands

    def _link_move_dest_ids_from_vals(self, vals):
        """Attach demand links from skipped create vals to the merged target MO."""
        self.ensure_one()
        dest_ids = self._extract_move_dest_command_ids(vals.get('move_dest_ids'))
        if not dest_ids:
            return

        dest_moves = self.env['stock.move'].browse(dest_ids).exists()
        for target_move in self.move_finished_ids.filtered(lambda move: move.state != 'cancel'):
            matching_dest_moves = dest_moves.filtered(
                lambda move: move.product_id == target_move.product_id
            )
            if matching_dest_moves:
                matching_dest_moves.write({'move_orig_ids': [(4, target_move.id)]})

    def _find_preemptive_target(self, vals, date_range):
        """Find an existing MO record that matches the creation values."""
        if self._is_auto_merge_protected_create_vals(vals):
            return None
        if self._is_backorder_create_vals(vals):
            return None

        product_id = vals.get('product_id')
        bom_id = vals.get('bom_id')
        if not product_id or not bom_id:
            return None

        # Extract context or default values
        picking_type_id = vals.get('picking_type_id') or self.env.context.get('default_picking_type_id')
        company_id = vals.get('company_id') or self.env.company.id
        date_start_str = vals.get('date_start')

        if not date_start_str:
            date_start = fields.Datetime.now()
        else:
            date_start = fields.Datetime.to_datetime(date_start_str)

        so_id = vals.get('source_sale_order_id')
        if not so_id:
            pg_id = vals.get('procurement_group_id')
            if pg_id:
                pg = self.env['procurement.group'].browse(pg_id)
                if pg.sale_id:
                    so_id = pg.sale_id.id
        if not so_id:
            origin = vals.get('origin')
            if origin:
                for part in (origin or '').split(','):
                    part = part.strip()
                    if part.startswith('SO'):
                        so = self.env['sale.order'].search([('name', '=', part)], limit=1)
                        if so:
                            so_id = so.id
                            break
        so_id = so_id or False

        domain = [
            ('bom_id', '=', bom_id),
            ('product_id', '=', product_id),
            ('state', 'in', ['draft', 'confirmed']),
            ('is_planned', '=', False),
            ('backorder_sequence', '=', 0),
            ('company_id', '=', company_id),
            ('source_sale_order_id', '=', so_id),
        ]
        if so_id:
            # MTO/SO demand must be consolidated by SO and product, regardless of
            # the parent branch date. This prevents one repeated component from
            # creating one MO per parent MO.
            pass
        else:
            date_from = date_start - timedelta(days=date_range)
            date_to = date_start + timedelta(days=date_range)
            domain.extend([
                ('date_start', '>=', date_from),
                ('date_start', '<=', date_to),
            ])

        if picking_type_id and not so_id:
            domain.append(('picking_type_id', '=', picking_type_id))

        if self.env.context.get('mps_no_mto_merge') or vals.get('is_mto') is False:
            domain.append(('is_mto', '=', False))

        # Return the most appropriate candidate (usually the earliest one)
        return self.search(domain, order='create_date asc', limit=1)

    def _merge_vals_into(self, vals):
        """Update existing MO with values from a prevented creation."""
        self.ensure_one()
        qty_to_add = vals.get('product_qty', 0.0)
        new_origin_part = vals.get('origin')

        new_origins = [self.origin] if self.origin else []
        if new_origin_part and new_origin_part not in new_origins:
            new_origins.append(new_origin_part)

        new_qty = self.product_qty + qty_to_add

        update_vals = {
            'product_qty': new_qty,
            'origin': ', '.join(new_origins) if new_origins else False,
        }

        # Note: source_sale_order_id is now part of the match, so it's already consistent

        _logger.info("Auto Merge (Pre-emptive): Merging %s units from originating %s into existing %s",
                     qty_to_add, new_origin_part, self.name)

        old_qty = self.product_qty
        self.with_context(skip_auto_merge=True).write(update_vals)
        self._link_move_dest_ids_from_vals(vals)

        if self.state in ('confirmed', 'progress', 'to_close') and old_qty > 0:
            # Recompute from the BoM instead of scaling existing raw moves.
            self._recompute_raw_moves_from_bom_for_auto_merge()

    def _try_merge_with_existing(self, date_range=None):
        self.ensure_one()
        if self.backorder_sequence:
            return self
        if not self.bom_id or self.state not in ('draft', 'confirmed'):
            return self
        if self.is_mto and not self.source_sale_order_id:
            return self
        if self.is_planned:
            return self

        if date_range is None:
            date_range = int(self.env['ir.config_parameter'].sudo().get_param(
                'mrp_auto_merge.date_range', '7'
            ))

        domain = [
            ('id', '!=', self.id),
            ('bom_id', '=', self.bom_id.id),
            ('product_id', '=', self.product_id.id),
            ('state', 'in', ['draft', 'confirmed']),
            ('is_planned', '=', False),
            ('backorder_sequence', '=', 0),
            ('company_id', '=', self.company_id.id),
            ('source_sale_order_id', '=', self.source_sale_order_id.id or False),
        ]
        if self.source_sale_order_id:
            # Same SO + same product/BoM should become one MO even when the
            # component is required by several parent MOs with different dates.
            pass
        else:
            date_from = self.date_start - timedelta(days=date_range)
            date_to = self.date_start + timedelta(days=date_range)
            domain.extend([
                ('picking_type_id', '=', self.picking_type_id.id),
                ('date_start', '>=', date_from),
                ('date_start', '<=', date_to),
            ])

        if self.env.context.get('mps_no_mto_merge'):
            domain.append(('is_mto', '=', False))

        candidates = self.search(domain, order='create_date asc')
        for candidate in candidates:
            if candidate.state in ('draft', 'confirmed'):
                self._merge_into(candidate)
                return candidate if not self.exists() else self
        return self

    def _merge_into(self, target_mo):
        self.ensure_one()
        if self.backorder_sequence or target_mo.backorder_sequence:
            _logger.info(
                "Auto Merge: skipping backorder merge between %s and %s",
                self.name,
                target_mo.name,
            )
            return

        source_so_id = self.source_sale_order_id.id or False
        target_source_so_id = target_mo.source_sale_order_id.id or False
        same_source_so = source_so_id == target_source_so_id
        unsafe_mto = (self.is_mto or target_mo.is_mto) and not source_so_id
        if not same_source_so or unsafe_mto:
            _logger.info(
                "Auto Merge: skipping cross-source merge between %s and %s",
                self.name,
                target_mo.name,
            )
            return

        qty_to_merge = self.product_qty
        new_origins = [target_mo.origin] if target_mo.origin else []
        if self.origin and self.origin not in new_origins:
            new_origins.append(self.origin)

        # 1. Update Target MO Quantity and Origin
        new_qty = target_mo.product_qty + qty_to_merge
        target_mo.with_context(skip_auto_merge=True).write({
            'product_qty': new_qty,
            'origin': ', '.join(new_origins) if new_origins else False,
        })

        # 2. Transfer MTO/Demand Links (Important for traceability and logic)
        # We need to make sure any move waiting for 'self' is now waiting for 'target_mo'
        for my_move in self.move_finished_ids:
            target_move = target_mo.move_finished_ids.filtered(lambda m: m.product_id == my_move.product_id)[:1]
            if target_move and my_move.move_dest_ids:
                # Add target move as a source for my destinations, and remove myself
                for dest in my_move.move_dest_ids:
                    dest.write({'move_orig_ids': [(4, target_move.id), (3, my_move.id)]})

        # Transfer upstream supply links (e.g. transfers feeding into this MO)
        for my_raw in self.move_raw_ids:
            target_raw = target_mo.move_raw_ids.filtered(lambda m: m.product_id == my_raw.product_id)[:1]
            if target_raw and my_raw.move_orig_ids:
                for orig in my_raw.move_orig_ids:
                    orig.write({'move_dest_ids': [(4, target_raw.id), (3, my_raw.id)]})

        # 3. Clean Slate: Cancel the current MO instead of deleting
        # Odoo 18 strictly prevents deleting moves that were linked to MTO operations.
        _logger.info("Auto Merge: Canceling redundant MO %s and merging %s units into %s",
                     self.name, self.product_qty, target_mo.name)

        # Odoo requires MO to be in 'cancel' state
        self.with_context(skip_auto_merge=True).write({'state': 'cancel'})
        self.move_raw_ids.with_context(skip_auto_merge=True).write({'state': 'cancel'})
        self.move_finished_ids.with_context(skip_auto_merge=True).write({'state': 'cancel'})

        # Clear links so downstream/upstream don't wait for this cancelled MO
        self.move_raw_ids.write({'move_orig_ids': [(5, 0, 0)], 'move_dest_ids': [(5, 0, 0)]})
        self.move_finished_ids.write({'move_orig_ids': [(5, 0, 0)], 'move_dest_ids': [(5, 0, 0)]})

        if target_mo.state in ('confirmed', 'progress', 'to_close'):
            # In Odoo 18, confirmed MOs do not recompute raw moves by onchange.
            # Rebuild BoM-based requirements with UoM rounding, then reserve again.
            target_mo._recompute_raw_moves_from_bom_for_auto_merge()
            for move in target_mo.move_finished_ids:
                if move.product_id == target_mo.product_id:
                    move.write({'product_uom_qty': target_mo.product_qty})

    def _round_qty_for_uom(self, qty, uom):
        rounding = uom.rounding if uom and uom.rounding and uom.rounding > 0 else 0.000001
        return float_round(qty or 0.0, precision_rounding=rounding)

    def _raw_move_recompute_key(self, vals=None, move=None):
        if move:
            return (
                move.bom_line_id.id or False,
                move.product_id.id,
                move.product_uom.id,
                move.operation_id.id or False,
            )
        return (
            vals.get('bom_line_id') or False,
            vals.get('product_id'),
            vals.get('product_uom'),
            vals.get('operation_id') or False,
        )

    def _prepare_raw_move_recompute_vals(self, vals):
        allowed_fields = {
            'name',
            'date',
            'date_deadline',
            'bom_line_id',
            'picking_type_id',
            'product_id',
            'product_uom_qty',
            'product_uom',
            'location_id',
            'location_dest_id',
            'raw_material_production_id',
            'company_id',
            'operation_id',
            'procure_method',
            'origin',
            'warehouse_id',
            'group_id',
            'propagate_cancel',
            'manual_consumption',
        }
        move_vals = {key: value for key, value in vals.items() if key in allowed_fields}
        uom = self.env['uom.uom'].browse(move_vals.get('product_uom'))
        move_vals['product_uom_qty'] = self._round_qty_for_uom(
            move_vals.get('product_uom_qty'),
            uom,
        )
        return move_vals

    def _recompute_raw_moves_from_bom_for_auto_merge(self):
        """Rebuild confirmed MO raw demand from the BoM after auto merge.

        The previous implementation multiplied existing raw moves by a ratio.
        That creates float artifacts and can drift from the BoM after repeated
        merges. This method unreserves, recomputes BoM lines, rounds by UoM,
        confirms newly created moves, then reserves again.
        """
        StockMove = self.env['stock.move']
        for production in self:
            if not production.bom_id:
                continue

            active_moves = production.move_raw_ids.filtered(
                lambda move: move.state not in ('done', 'cancel')
            )
            if active_moves:
                active_moves._do_unreserve()

            moves_by_key = {}
            for move in active_moves.filtered('bom_line_id'):
                moves_by_key.setdefault(production._raw_move_recompute_key(move=move), StockMove)
                moves_by_key[production._raw_move_recompute_key(move=move)] |= move

            expected_vals_list = production._get_moves_raw_values()
            touched_moves = StockMove
            new_moves = StockMove

            for vals in expected_vals_list:
                move_vals = production._prepare_raw_move_recompute_vals(vals)
                key = production._raw_move_recompute_key(vals=move_vals)
                existing = moves_by_key.get(key, StockMove)[:1]
                if existing:
                    existing.with_context(skip_auto_merge=True).write(move_vals)
                    touched_moves |= existing
                else:
                    move_vals['state'] = 'draft'
                    new_move = StockMove.with_context(skip_auto_merge=True).create(move_vals)
                    new_moves |= new_move
                    touched_moves |= new_move

            obsolete_moves = active_moves.filtered(
                lambda move: move.bom_line_id and move not in touched_moves
            )
            if obsolete_moves:
                obsolete_moves._action_cancel()

            if touched_moves:
                touched_moves._adjust_procure_method()
                draft_moves = touched_moves.filtered(lambda move: move.state == 'draft')
                if draft_moves:
                    draft_moves._action_confirm(merge=False)
                touched_moves.filtered(
                    lambda move: move.state not in ('done', 'cancel')
                )._action_assign()

            if new_moves:
                production.message_post(body=_(
                    "Auto Merge recomputed BoM requirements and created %s missing raw material move(s)."
                ) % len(new_moves))

    def _get_check_availability_diagnostic_lines(self):
        self.ensure_one()
        Quant = self.env['stock.quant'].sudo()
        lines = []
        for move in self.move_raw_ids.filtered(lambda m: m.state not in ('done', 'cancel')):
            rounding = move.product_uom.rounding or 0.000001
            if float_round(move.product_uom_qty - move.quantity, precision_rounding=rounding) <= 0:
                continue

            product = move.product_id
            source_location = move.location_id or self.location_src_id
            free_qty_product_uom = Quant._get_available_quantity(
                product,
                source_location,
                strict=False,
            )
            free_qty = product.uom_id._compute_quantity(free_qty_product_uom, move.product_uom)
            on_hand_qty = product.uom_id._compute_quantity(
                product.with_context(location=source_location.id).qty_available,
                move.product_uom,
            )
            quant_domain = [
                ('product_id', '=', product.id),
                ('location_id', 'child_of', source_location.id),
            ]
            quants = Quant.search(quant_domain)
            reserved_quant_qty = product.uom_id._compute_quantity(
                sum(quants.mapped('reserved_quantity')),
                move.product_uom,
            )
            lot_names = ', '.join(quants.mapped('lot_id.name')[:5]) or '-'
            owner_names = ', '.join(quants.mapped('owner_id.display_name')[:5]) or '-'
            package_names = ', '.join(quants.mapped('package_id.name')[:5]) or '-'

            if move.procure_method == 'make_to_order' and move.move_orig_ids:
                reason = _("รอของจากขั้นตอนก่อนหน้า (Waiting for upstream supply)")
            elif on_hand_qty <= 0:
                reason = _("ไม่มีของในคลังต้นทาง (No on-hand stock at source)")
                warehouse = self.picking_type_id.warehouse_id
                if warehouse and warehouse.lot_stock_id and warehouse.lot_stock_id.id != source_location.id:
                    wh_on_hand = product.with_context(location=warehouse.lot_stock_id.id).qty_available
                    if wh_on_hand > 0:
                        reason += _(" | 💡 พบของ %s %s ใน %s") % (wh_on_hand, move.product_uom.name, warehouse.lot_stock_id.display_name)

                pending_receipt = self.env['stock.move'].search([
                    ('product_id', '=', product.id),
                    ('picking_id.picking_type_id.code', '=', 'incoming'),
                    ('state', 'in', ('assigned', 'confirmed', 'partially_available')),
                ], limit=1)
                if pending_receipt:
                    reason += _(" | 💡 มีรายการรับเข้า %s") % (pending_receipt.reference)
            elif free_qty < (move.product_uom_qty - move.quantity):
                reason = _("มีของในคลังแต่ถูกจองโดยรายการอื่นไปหมดแล้ว (On-hand exists but reserved by others)")
            elif product.tracking != 'none' and not lot_names:
                reason = _("สินค้าต้องระบุ Lot/Serial (Tracked product requires lot/serial)")
            else:
                reason = _("ตรวจสอบเงื่อนไขอื่นๆ เช่น Lot, Package, หรือ Owner")

            lines.append(_(
                "%(product)s (คลัง: %(source)s)\n"
                "- ต้องการ: %(demand).6g %(uom)s (จองแล้ว: %(reserved).6g %(uom)s)\n"
                "- ในคลัง: %(onhand).6g %(uom)s (ว่างอยู่: %(free).6g %(uom)s)\n"
                "- 👉 สาเหตุ: %(reason)s"
            ) % {
                'product': product.display_name,
                'source': source_location.display_name,
                'demand': move.product_uom_qty,
                'reserved': move.quantity,
                'onhand': on_hand_qty,
                'free': free_qty,
                'quant_reserved': reserved_quant_qty,
                'uom': move.product_uom.name,
                'procure': move.procure_method,
                'tracking': product.tracking,
                'lots': lot_names,
                'owners': owner_names,
                'packages': package_names,
                'reason': reason,
            })
        return lines

    def action_assign(self):
        res = super().action_assign()
        if self.env.context.get('skip_check_availability_diagnostic'):
            return res

        for production in self:
            lines = production._get_check_availability_diagnostic_lines()
            if not lines:
                continue
            body = Markup("<b>%s</b><ul>%s</ul>") % (
                _("Check Availability diagnostic: components still not fully reserved."),
                Markup("").join(
                    Markup("<li>%s</li>") % Markup.escape(line).replace('\n', Markup('<br/>'))
                    for line in lines[:10]
                ),
            )
            production.message_post(body=body)
        return res

    def button_smart_unplan(self):
        """Wolapart Edition: Smart Unplan v16 (Recursive Chain)
        Recursively unplans the entire production chain to reset the schedule.
        """
        initial_selection = self.filtered(lambda mo: mo.state not in ('done', 'cancel'))
        if not initial_selection:
            return True

        orders_to_unplan = initial_selection._get_full_production_chain()
        orders_already_planned = orders_to_unplan.filtered('is_planned')

        if orders_already_planned:
            _logger.info("Smart Unplan: Unplanning %s orders in chain.", len(orders_already_planned))
            orders_already_planned.button_unplan()

        return True

    def button_plan(self):
        """Wolapart Edition: Smart Planning v5 (Full Recursive + Kill-Switch)
        - Kill-Switch: Set 'mrp.use_smart_planning' to 'False' to use Core 100%
        - Recursively expands selection to include the whole production tree.
        - Ensures children are planned BEFORE parents.
        - Prioritizes MTO over MTS.
        - Unplans existing schedules for the whole chain to avoid conflicts.
        """
        use_smart = self.env['ir.config_parameter'].sudo().get_param(
            'mrp.use_smart_planning', 'True'
        )
        if use_smart != 'True':
            _logger.info("Smart Planning DISABLED. Using Odoo Core button_plan.")
            return super().button_plan()

        initial_selection = self.filtered(lambda mo: mo.state not in ('done', 'cancel'))
        if not initial_selection:
            return super().button_plan()

        # 1. Recursive Expansion: Find all related MOs in the tree
        orders_to_plan = initial_selection._get_full_production_chain()
        _logger.info("Smart Planning: Expanded %s records to %s total records in chain.",
                     len(initial_selection), len(orders_to_plan))

        # 2. Clean Slate: Unplan selection to free up slots
        orders_already_planned = orders_to_plan.filtered('is_planned')
        if orders_already_planned:
            _logger.info("Smart Planning: Unplanning %s already planned orders.", len(orders_already_planned))
            orders_already_planned.button_unplan()

        # 3. Confirm draft orders in the whole chain
        orders_to_confirm = orders_to_plan.filtered(lambda mo: mo.state == 'draft')
        if orders_to_confirm:
            _logger.info("Smart Planning: Confirming %s draft orders.", len(orders_to_confirm))
            orders_to_confirm.action_confirm()

        # 4. Build Dependency Graph (Prerequisite -> Dependant)
        # graph[A] = [B, C] means B and C depend on A (A must finish before they start)
        graph = {mo: self.env['mrp.production'] for mo in orders_to_plan}

        # Pre-index for performance to avoid O(N^2) filtered lookups
        mo_by_name = {mo.name: mo for mo in orders_to_plan if mo.name}

        # Pre-index Product Consumers: product_id -> MOs in our selection that consume it
        consumers_by_product = {}
        for m in orders_to_plan:
            for p_id in m.move_raw_ids.mapped('product_id').ids:
                if p_id not in consumers_by_product:
                    consumers_by_product[p_id] = self.env['mrp.production']
                consumers_by_product[p_id] |= m

        for mo in orders_to_plan:
            successors = self.env['mrp.production']

            # A) Origin-based Successors: I supply my parents mentioned in my origin
            if mo.origin:
                origin_names = [x.strip() for x in mo.origin.split(',')]
                for name in origin_names:
                    if name in mo_by_name and mo_by_name[name] != mo:
                        successors |= mo_by_name[name]

            # B) Move-based Successors: Things that consume my finished moves
            successors |= mo.move_finished_ids.move_dest_ids.raw_material_production_id.filtered(lambda m: m in orders_to_plan)

            # C) Product-based Successors: Any MO in our selection that uses my product as a component
            # Optimized O(1) primary lookup using pre-indexed map
            p_id = mo.product_id.id
            potential_successors = consumers_by_product.get(p_id, self.env['mrp.production'])
            successors |= (potential_successors - mo)

            graph[mo] |= successors

        # 5. Topological Sort (returns Prerequisites before Dependants -> Children before Parents)
        # Tie-breaker: Prefer larger MO numbers (usually children) to start earlier if independent.
        sorted_keys = sorted(
            graph.keys(),
            key=lambda m: (1 if m.is_mto else 0, int(''.join(filter(str.isdigit, m.name or '0')) or 0)),
            reverse=True
        )
        ordered_graph = {k: graph[k] for k in sorted_keys}
        sorted_orders = topological_sort(ordered_graph)

        # 6. Origin Propagation (Source 100% Tracking)
        # Roots are MOs that no one in this specific graph depends on (e.g. FG)
        all_successors = set()
        for successors in graph.values():
            all_successors.update(successors.ids)
        roots = [m for m in sorted_orders if m.id not in all_successors]

        for root in roots:
            todo_desc = list(graph[root])
            desc_chain = set()
            while todo_desc:
                curr = todo_desc.pop(0)
                if curr in desc_chain:
                    continue
                desc_chain.add(curr)
                todo_desc.extend(list(graph[curr]))

            for desc in desc_chain:
                if root.name not in (desc.origin or ''):
                    new_origin = (desc.origin + ', ' + root.name) if desc.origin else root.name
                    desc.write({'origin': new_origin})

        # 7. Execute Planning in JIT Multi-Workcenter Path
        now = fields.Datetime.now()
        machine_availability = {}  # wc_id -> datetime

        _logger.info("Smart Planning v15 (JIT Multi-Machine): Planning %s MOs.", len(sorted_orders))

        for order in sorted_orders:
            # 1. Material Dependency: When do my children finish?
            my_prerequisites = [mo for mo, deps in graph.items() if order in deps]
            prereq_dates = [c.date_finished for c in my_prerequisites if c.date_finished]

            # Also check direct moves for external dependencies
            move_prereq_dates = order._get_planned_child_dates_from_moves()
            prereq_dates += [d for d in move_prereq_dates if d]

            material_ready = max(prereq_dates) + timedelta(seconds=10) if prereq_dates else now

            # 2. Machine Availability: When is my specific machine free?
            # We look at the first operation as a proxy for the 'primary' workcenter
            wc_id = order.bom_id.operation_ids[:1].workcenter_id.id
            machine_ready = now

            if wc_id:
                if wc_id not in machine_availability:
                    # Sync with current shop floor state for THIS specific machine
                    latest_wo = self.env['mrp.workorder'].search([
                        ('workcenter_id', '=', wc_id),
                        ('state', 'not in', ('cancel', 'done')),
                        ('production_id', 'not in', orders_to_plan.ids)
                    ], order='date_finished desc', limit=1)
                    machine_ready = latest_wo.date_finished + timedelta(seconds=10) if latest_wo and latest_wo.date_finished else now
                else:
                    machine_ready = machine_availability[wc_id] + timedelta(seconds=10)

            # 3. JIT Start: Earliest possible slot where BOTH machine and materials are ready
            target_start = max(material_ready, machine_ready, now)

            # Force Plan
            order.with_context(force_date=True).write({'date_start': target_start})
            order._plan_workorders()

            # 4. Update Machine State: Track when this machine will be free again
            if wc_id:
                machine_availability[wc_id] = order.date_finished

            _logger.info("Smart Planning v15: JIT Plan %s on WC %s (Start: %s, Finish: %s)",
                         order.name, wc_id, target_start, order.date_finished)


        return True

    def _get_full_production_chain(self):
        """Recursively find all linked MOs in the hierarchy.
        Enhanced detection via: Origin, Moves, Product (Component), Procurement Group.
        """
        chain = self.browse()
        todo = self

        while todo:
            current = todo[0]
            todo -= current
            if current in chain or current.state in ('done', 'cancel'):
                continue
            chain |= current

            # 1. Biological Children (Moves)
            children_moves = current.move_raw_ids.move_orig_ids.production_id

            # 2. Logic Children (Origin)
            children_origin = self.search([
                ('origin', 'ilike', current.name),
                ('state', 'not in', ('cancel', 'done'))
            ]).filtered(lambda m: current.name in [x.strip() for x in (m.origin or '').split(',')])

            # 3. Component Matching (The "Missing Link" fix)
            current_comp_ids = current.move_raw_ids.mapped('product_id').ids
            children_by_product = self.browse()
            if current_comp_ids:
                domain = [
                    ('product_id', 'in', current_comp_ids),
                    ('state', 'not in', ('cancel', 'done')),
                    ('id', 'not in', chain.ids),
                ]
                if current.mps_batch_id:
                    domain.append(('mps_batch_id', '=', current.mps_batch_id.id))
                children_by_product = self.search(domain)

            # 4. Parents (Moves)
            parents_moves = current.move_finished_ids.move_dest_ids.raw_material_production_id

            # 5. Parents (Origin)
            parents_origin = self.browse()
            if current.origin:
                origin_parts = [x.strip() for x in current.origin.split(',')]
                parent_names = [p for p in origin_parts if '/MO/' in p]
                if parent_names:
                    parents_origin = self.search([
                        ('name', 'in', parent_names),
                        ('state', 'not in', ('cancel', 'done'))
                    ])

            links = (children_moves | children_origin | children_by_product | parents_moves | parents_origin) - chain
            todo |= links

        return chain

    def _get_child_productions_from_moves(self):
        self.ensure_one()
        return self.move_raw_ids.move_orig_ids.production_id

    def _get_planned_child_dates_from_moves(self):
        self.ensure_one()
        dates = []
        seen_moves = set()

        def collect_dates(moves):
            for move in moves:
                if move.id in seen_moves:
                    continue
                seen_moves.add(move.id)
                if move.production_id and move.production_id.is_planned:
                    dates.append(move.production_id.date_finished)
                elif move.move_orig_ids:
                    collect_dates(move.move_orig_ids)

        collect_dates(self.move_raw_ids)
        return dates

class MrpProductionSchedule(models.Model):
    _inherit = 'mrp.production.schedule'

    def action_replenish(self, based_on_lead_time=False):
        """Wolapart Edition: Selective MTO Merge Guard.
        - Purple 'Order' button (Mass) uses based_on_lead_time=True.
        - Line 'Order' button (Single) uses based_on_lead_time=False.
        We prevent MTO merge for mass orders to avoid 'doubling' and planning mess.
        """
        if based_on_lead_time:
            self = self.with_context(mps_no_mto_merge=True)
        return super().action_replenish(based_on_lead_time=based_on_lead_time)

    def _get_incoming_qty(self, date_range):
        """Wolapart Edition: Recognize Draft MTO MOs in MPS.
        Standard Odoo ignores Draft moves, which causes MPS to suggest
        duplicates for MTO orders that start in Draft state.
        """
        incoming_qty, incoming_qty_done = super()._get_incoming_qty(date_range)

        # Search for Draft MTO Manufacturing Orders
        # We use the 'is_mto' field we added earlier
        domain = [
            ('state', '=', 'draft'),
            ('is_mto', '=', True),
            ('product_id', 'in', self.mapped('product_id').ids),
            ('picking_type_id', 'in', self.mapped('warehouse_id.manu_type_id').ids),
        ]

        draft_mos = self.env['mrp.production'].search(domain)
        if not draft_mos:
            return incoming_qty, incoming_qty_done

        # Map MOs to the MPS periods
        for mo in draft_mos:
            # Find the period this MO falls into
            for index, (d_start, d_stop) in enumerate(date_range):
                # Typically MPS uses date_start for MOs it creates,
                # but MTO MOs follow SO dates. We check if it lands in the window.
                mo_date = mo.date_start.date() if mo.date_start else fields.Date.today()
                if d_start <= mo_date <= d_stop:
                    key = (date_range[index], mo.product_id, mo.picking_type_id.warehouse_id)
                    incoming_qty[key] += mo.product_qty
                    break

        return incoming_qty, incoming_qty_done
