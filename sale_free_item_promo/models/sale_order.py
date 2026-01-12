# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.fields import Command
from odoo.tools import float_compare, float_round, float_is_zero, format_datetime

class ResPartner(models.Model):
    _inherit = "res.partner"

    free_item_promo_eligible = fields.Boolean(
        string="Eligible for Free Item Promo",
        help="If enabled, free item lines will be added automatically on quotations/orders according to product settings.",
    )


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    is_free_item = fields.Boolean(
        string="Is Free Item",
        default=False,
        copy=False,
        help="Technical flag to mark lines that were created as free promotional items.",
    )

    def unlink(self):
        orders_to_block = self.filtered(lambda l: l.is_free_item and l.order_id)
        if orders_to_block:
            for order in orders_to_block.mapped("order_id"):
                # Only block on persisted orders; for unsaved orders, recompute will handle naturally
                if not order.id:
                    continue
                prods = orders_to_block.filtered(lambda l, o=order: l.order_id == o).mapped("product_id").ids
                if prods:
                    order.with_context(skip_free_item_recompute=True).write({
                        "free_item_block_ids": [(4, pid) for pid in prods],
                    })
        return super().unlink()


class SaleOrder(models.Model):
    _inherit = "sale.order"

    free_item_block_ids = fields.Many2many(
        comodel_name="product.product",
        string="Blocked Free Item Products",
        help="Technical: products whose free lines were manually removed; cleared when non-free lines change.",
        copy=False,
    )

   # ---------- Helpers ----------
    def _get_free_item_map(self):
        """
        Map: {free_product (product.product): target_free_qty}
        Computed from NON-free lines whose templates enable the promo (Buy-X-Get-Y).
        """
        self.ensure_one()
        free_map = {}

        base_lines = self.order_line.filtered(
            lambda l: not l.is_free_item
            and l.product_id
            and l.product_id.product_tmpl_id.enable_free_item
        )
        for line in base_lines:
            tmpl = line.product_id.product_tmpl_id
            free_product = tmpl.free_item_product_id
            if not free_product:
                continue

            buy_qty_per_unit = tmpl.buy_item_qty or 1.0
            if not buy_qty_per_unit:
                continue

            free_qty_per_unit = tmpl.free_item_qty or 0.0
            blocks = (line.product_uom_qty or 0.0) // buy_qty_per_unit
            if blocks <= 0:
                continue

            total_free_qty = blocks * free_qty_per_unit
            free_map[free_product] = free_map.get(free_product, 0.0) + total_free_qty

        return free_map

    def _make_free_line_vals(self, product, qty):
        """Zero-price free line (no Odoo discount)."""
        return {
            "name": f"[FREE] {product.display_name}",
            "product_id": product.id,
            "product_uom": product.uom_id.id,
            "product_uom_qty": qty,
            "price_unit": 0.0,
            "discount": 0.0,
            "is_free_item": True,
            # "tax_id": [(6, 0, product.taxes_id.ids)],
        }

    def _snapshot_nonfree(self):
        """Snapshot only NON-free lines to detect meaningful changes."""
        snap, new_idx = {}, 0
        for l in self.order_line:
            if l.is_free_item:
                continue
            key = l.id or f"new#{new_idx}"
            if not l.id:
                new_idx += 1
            snap[key] = (l.product_id.id, float(l.product_uom_qty or 0.0))
        return snap

    # ---------- Core recompute (UPSERT) ----------
    def _recompute_free_item_lines(self):
        """
        Sync free lines with current NON-free lines:
        - For each (product -> target_qty) in free_map:
            * Update existing free line qty OR create it if missing.
        - Remove any free lines whose product is not in free_map.
        Only the inner unlink/write/update calls are context-guarded to avoid recursion.
        """
        for order in self:
            if order.free_item_block_ids and not self.env.context.get("force_free_item_recompute"):
                # User deleted promo lines; skip auto-regeneration unless explicitly forced
                continue
            # Optional eligibility gate
            if not order.partner_id:
                fl = order.order_line.filtered("is_free_item")
                if order.id:
                    fl.with_context(skip_free_item_recompute=True).unlink()
                else:
                    cmds = [Command.unlink(l.id) if l.id else Command.delete(0) for l in fl] if fl else []
                    if cmds:
                        order.with_context(skip_free_item_recompute=True).update({"order_line": cmds})
                continue

            free_map = order._get_free_item_map()
            if order.free_item_block_ids:
                blocked = set(order.free_item_block_ids.ids)
                free_map = {p: qty for p, qty in free_map.items() if p.id not in blocked}

            # Index existing free lines by product
            existing = {
                l.product_id: l
                for l in order.order_line.filtered(lambda l: l.is_free_item and l.product_id)
            }

            if not order.id:
                # ------- UNSAVED (form): upsert/remove via in-memory commands -------
                commands = []

                # upsert/update
                for product, target_qty in free_map.items():
                    if target_qty <= 0:
                        continue
                    ex = existing.get(product)
                    vals = order._make_free_line_vals(product, target_qty)
                    if ex:
                        # mutate transient record (no DB write)
                        ex.product_uom_qty = target_qty
                        ex.name = vals["name"]
                        ex.price_unit = 0.0
                        ex.discount = 0.0
                        ex.is_free_item = True
                    else:
                        commands.append(Command.create(vals))

                # remove obsolete free lines
                for l in order.order_line.filtered(lambda l: l.is_free_item and l.product_id not in free_map):
                    commands.append(Command.unlink(l.id) if l.id else Command.delete(0))

                if commands:
                    order.with_context(skip_free_item_recompute=True).update({"order_line": commands})

            else:
                # ------- PERSISTED: upsert/remove with real writes -------
                # upsert/update
                for product, target_qty in free_map.items():
                    if target_qty <= 0:
                        continue
                    ex = existing.get(product)
                    vals = order._make_free_line_vals(product, target_qty)
                    if ex:
                        need = (
                            not float_is_zero((ex.product_uom_qty or 0.0) - target_qty,
                                              precision_rounding=ex.product_uom.rounding)
                            or ex.name != vals["name"]
                            or ex.price_unit != 0.0
                            or ex.discount != 0.0
                            or not ex.is_free_item
                        )
                        if need:
                            ex.with_context(skip_free_item_recompute=True).write({
                                "product_uom_qty": target_qty,
                                "name": "[FREE]" + vals["name"],
                                "price_unit": 0.0,
                                "discount": 0.0,
                                "is_free_item": True,
                            })
                    else:
                        order.with_context(skip_free_item_recompute=True).write({
                            "order_line": [Command.create(vals)]
                        })

                # remove obsolete
                to_remove = order.order_line.filtered(lambda l: l.is_free_item and l.product_id not in free_map)
                if to_remove:
                    to_remove.with_context(skip_free_item_recompute=True).unlink()

    def _update_order_line_info(self, product_id, quantity, **kwargs):
        """
        Ensure catalog-driven product edits also refresh free promo lines.
        Mirrors the behavior of form onchanges/order write: clear blocklist and recompute
        when NON-free content actually changed.
        """
        self.ensure_one()
        before = self._snapshot_nonfree()

        price = super()._update_order_line_info(product_id, quantity, **kwargs)
        if self.env.context.get("skip_free_item_recompute"):
            return price

        after = self._snapshot_nonfree()
        if after != before:
            self.write({"free_item_block_ids": [(5, 0, 0)]})
            self.with_context(force_free_item_recompute=True)._recompute_free_item_lines()

        return price

    # ---------- Onchanges ----------
    @api.onchange("order_line")
    def _onchange_order_line_recompute_free_items(self):
        """
        Prevent bounce-back:
        - NEW (unsaved) orders: do nothing on onchange → user can delete free lines; they won’t reappear
          until save or until a NON-free change later.
        - SAVED orders: only recompute if NON-free lines changed vs _origin (product/qty add/remove).
          Deleting a free line alone will NOT trigger recompute.
        """
        if self.env.context.get("skip_free_item_recompute"):
            return

        for order in self:
            # If user removed free lines, block those products immediately (no recompute)
            origin_free_products = {
                l.product_id.id for l in order._origin.order_line if l.is_free_item and l.product_id
            }
            current_free_products = {
                l.product_id.id for l in order.order_line if l.is_free_item and l.product_id
            }
            removed_products = origin_free_products - current_free_products
            if removed_products:
                order.free_item_block_ids = [(4, pid) for pid in removed_products]

            # Compare NON-free between origin and current (include unsaved/new lines)
            orig_nonfree = sorted([
                (l.product_id.id, float(l.product_uom_qty or 0.0))
                for l in order._origin.order_line if not l.is_free_item
            ])
            curr_nonfree = sorted([
                (l.product_id.id, float(l.product_uom_qty or 0.0))
                for l in order.order_line if not l.is_free_item
            ])

            if orig_nonfree != curr_nonfree:
                # non-free changed → clear blocks and recompute
                if order.free_item_block_ids:
                    order.free_item_block_ids = [(5, 0, 0)]
                order.with_context(force_free_item_recompute=True)._recompute_free_item_lines()

    # ---------- CRUD hooks ----------
    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        # Initial build after create (optional freshness helpers)
        if hasattr(self.env, "flush_all"):
            self.env.flush_all()
        if hasattr(self.env, "invalidate_all"):
            self.env.invalidate_all()
        orders._recompute_free_item_lines()
        return orders

    def write(self, vals):
        """
        Recompute AFTER write only if NON-free changed (or partner changed).
        Deleting a free line alone won’t cause a rebuild.
        Changing qty 6→9 will upsert and override free qty 2→3.
        """
        # Snapshot NON-free before
        before = {o.id: o._snapshot_nonfree() for o in self}

        res = super().write(vals)
        if self.env.context.get("skip_free_item_recompute"):
            return res

        partner_touched = "partner_id" in vals

        # Fresh read if available
        if hasattr(self.env, "flush_all"):
            self.env.flush_all()
        if hasattr(self.env, "invalidate_all"):
            self.env.invalidate_all()

        need_ids = []
        for order in self:
            after = order._snapshot_nonfree()
            if partner_touched or after != before.get(order.id, {}):
                need_ids.append(order.id)

        if need_ids:
            orders = self.browse(need_ids)
            # Non-free changed: clear blocklist and recompute
            orders.write({"free_item_block_ids": [(5, 0, 0)]})
            orders.with_context(force_free_item_recompute=True)._recompute_free_item_lines()

        return res
