import logging
from datetime import timedelta

from odoo import api, fields, models
from odoo.tools.misc import topological_sort

_logger = logging.getLogger(__name__)


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

    def _find_root_mo(self, mo_cache=None):
        self.ensure_one()
        if mo_cache is not None and self in mo_cache:
            return mo_cache[self]

        if not self.origin:
            res = self
        else:
            origin_parts = [x.strip() for x in self.origin.split(',')]
            if not origin_parts:
                res = self
            else:
                first_origin = origin_parts[0]
                # Skip SO origins when looking for Root MO, we want the highest MO
                if first_origin.startswith('SO') or first_origin.startswith('S0'):
                    res = self
                elif first_origin.startswith('GMP/MO/') or first_origin.startswith('M-WH/MO/') or first_origin.startswith('WH/MO/'):
                    parent_mo = self.search([('name', '=', first_origin)], limit=1)
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
            # 2. Check Origin (Support for merged or propagated SO names)
            origin_parts = [x.strip() for x in self.origin.split(',')]
            for part in origin_parts:
                if part.startswith('SO') or part.startswith('S0'):
                    # Search by name with cache
                    if so_cache is not None and part in so_cache:
                        so = so_cache[part]
                    else:
                        so = self.env['sale.order'].search([('name', '=', part)], limit=1)
                        if so_cache is not None:
                            so_cache[part] = so
                    if so:
                        break

            # 3. Traversal (Check parent MO)
            if not so:
                first_origin = origin_parts[0].strip()
                if first_origin.startswith('WH/MO/') or first_origin.startswith('GMP/MO/') or first_origin.startswith('M-WH/MO/'):
                    parent = self.search([('name', '=', first_origin)], limit=1)
                    if parent:
                        so = parent._find_source_so(mo_cache=mo_cache, so_cache=so_cache)

        if mo_cache is not None:
            mo_cache[self] = so
        return so or self.env['sale.order']

    @api.model_create_multi
    def create(self, vals_list):
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

        # We need a predictable key for grouping
        def get_merge_key(v):
            p_id = v.get('product_id')
            b_id = v.get('bom_id')
            c_id = v.get('company_id') or self.env.company.id
            pt_id = v.get('picking_type_id') or self.env.context.get('default_picking_type_id')
            so_id = v.get('source_sale_order_id') or False
            # Bucket date into a rough start date for fuzzy matching
            d_str = v.get('date_start')
            if not d_str:
                d_dt = fields.Datetime.now()
            else:
                d_dt = fields.Datetime.to_datetime(d_str)
            return (p_id, b_id, c_id, pt_id, so_id, d_dt.date())

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
            new_records = super().create(raw_vals)
            for (original_idx, _), record in zip(to_create_list, new_records):
                created_records[original_idx] = record
                result_map[original_idx] = ('newly_created', record)

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

    def _find_preemptive_target(self, vals, date_range):
        """Find an existing MO record that matches the creation values."""
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

        date_from = date_start - timedelta(days=date_range)
        date_to = date_start + timedelta(days=date_range)
        so_id = vals.get('source_sale_order_id') or False

        domain = [
            ('bom_id', '=', bom_id),
            ('product_id', '=', product_id),
            ('state', 'in', ['draft', 'confirmed']),
            ('is_planned', '=', False),
            ('company_id', '=', company_id),
            ('date_start', '>=', date_from),
            ('date_start', '<=', date_to),
            ('source_sale_order_id', '=', so_id),
        ]
        if picking_type_id:
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

        if self.state == 'confirmed' and old_qty > 0:
            # Re-calculate raw moves for the new total quantity
            self._update_raw_moves(new_qty / old_qty)

    def _try_merge_with_existing(self, date_range=None):
        self.ensure_one()
        if not self.bom_id or self.state not in ('draft', 'confirmed'):
            return
        if self.is_planned:
            return

        if date_range is None:
            date_range = int(self.env['ir.config_parameter'].sudo().get_param(
                'mrp_auto_merge.date_range', '7'
            ))

        date_from = self.date_start - timedelta(days=date_range)
        date_to = self.date_start + timedelta(days=date_range)

        domain = [
            ('id', '!=', self.id),
            ('bom_id', '=', self.bom_id.id),
            ('product_id', '=', self.product_id.id),
            ('state', 'in', ['draft', 'confirmed']),
            ('is_planned', '=', False),
            ('picking_type_id', '=', self.picking_type_id.id),
            ('company_id', '=', self.company_id.id),
            ('date_start', '>=', date_from),
            ('date_start', '<=', date_to),
        ]
        if self.env.context.get('mps_no_mto_merge'):
            domain.append(('is_mto', '=', False))

        candidates = self.search(domain, order='create_date asc')
        for candidate in candidates:
            if candidate.state in ('draft', 'confirmed'):
                self._merge_into(candidate)
                break

    def _merge_into(self, target_mo):
        self.ensure_one()
        new_origins = [target_mo.origin] if target_mo.origin else []
        if self.origin and self.origin not in new_origins:
            new_origins.append(self.origin)

        # 1. Update Target MO Quantity and Origin
        new_qty = target_mo.product_qty + self.product_qty
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

        # 3. Clean Slate: Delete the current MO instead of canceling
        # This keeps the list view clean as requested.
        _logger.info("Auto Merge: Deleting redundant MO %s and merging %s units into %s",
                     self.name, self.product_qty, target_mo.name)

        # Odoo requires MO to be in 'cancel' state before deletion
        # We also need to clear move links to allow smooth deletion
        self.with_context(skip_auto_merge=True).write({'state': 'cancel'})
        self.move_raw_ids.with_context(skip_auto_merge=True).write({'state': 'cancel'})
        self.move_finished_ids.with_context(skip_auto_merge=True).write({'state': 'cancel'})

        self.move_raw_ids.unlink()
        self.move_finished_ids.unlink()
        self.with_context(skip_auto_merge=True).unlink()

        if target_mo.state == 'confirmed':
            # In Odoo 18, _onchange_product_qty is gone.
            # We must update moves manually if confirmed because compute skips non-draft MOs.
            target_mo._update_raw_moves(new_qty / (target_mo.product_qty - self.product_qty))
            for move in target_mo.move_finished_ids:
                if move.product_id == target_mo.product_id:
                    move.write({'product_uom_qty': target_mo.product_qty})

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
