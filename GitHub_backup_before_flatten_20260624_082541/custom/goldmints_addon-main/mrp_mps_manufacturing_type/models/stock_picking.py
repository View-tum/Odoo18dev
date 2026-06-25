import re
from odoo import api, fields, models
from odoo.tools.float_utils import float_compare, float_is_zero


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    manufacturing_type = fields.Selection([
        ('plastic', 'Plastic'),
        ('pharma', 'Pharma'),
        ('packaging', 'Packaging'),
    ], string='Manufacturing Type', readonly=True, copy=False)

    def _get_manufacturing_type_from_group(self, group_id):
        if not group_id:
            return False

        productions = self.env['mrp.production'].search([
            ('procurement_group_id', '=', group_id),
        ])
        manufacturing_types = {
            production.manufacturing_type
            for production in productions
            if production.manufacturing_type
        }
        return manufacturing_types.pop() if len(manufacturing_types) == 1 else False

    def action_open_manual_merge_internal_transfers(self):
        pickings = self.filtered(
            lambda picking: picking.picking_type_id.code == "internal"
            and picking.state not in ("done", "cancel")
        )
        return {
            "type": "ir.actions.act_window",
            "name": "Merge Internal Transfers",
            "res_model": "stock.picking.manual.merge.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_picking_ids": [(6, 0, pickings.ids)],
            },
        }

    def action_cancel(self):
        canceling_production_ids = self.env.context.get("canceling_mrp_production_ids")
        if not canceling_production_ids:
            return super().action_cancel()

        canceling_productions = self.env["mrp.production"].browse(canceling_production_ids)
        shared_pickings = self._get_shared_mo_internal_transfer_pickings(canceling_productions)
        pickings_to_cancel = self - shared_pickings
        if pickings_to_cancel:
            return super(StockPicking, pickings_to_cancel).action_cancel()
        return True

    def _get_shared_mo_internal_transfer_pickings(self, canceling_productions):
        return self.filtered(
            lambda picking: picking.picking_type_id.code == "internal"
            and picking.state not in ("done", "cancel")
            and bool(
                picking.production_ids.filtered(
                    lambda production: production not in canceling_productions
                    and production.state != "cancel"
                )
            )
        )

    def _sync_shared_mo_internal_transfer_quantities(self):
        for picking in self.filtered(
            lambda item: item.picking_type_id.code == "internal"
            and item.state not in ("done", "cancel")
        ):
            active_productions = picking.production_ids.filtered(lambda production: production.state != "cancel")
            if not active_productions:
                super(StockPicking, picking).action_cancel()
                continue
            for move in picking.move_ids.filtered(lambda item: item.state not in ("done", "cancel")):
                raw_moves = move.move_dest_ids.filtered(
                    lambda raw: raw.raw_material_production_id in active_productions
                    and raw.state != "cancel"
                    and raw.product_id == move.product_id
                    and raw.product_uom == move.product_uom
                )
                if not raw_moves:
                    raw_moves = active_productions.move_raw_ids.filtered(
                        lambda raw: raw.state != "cancel"
                        and raw.product_id == move.product_id
                        and raw.product_uom == move.product_uom
                    )

                quantity = sum(raw_moves.mapped("product_uom_qty"))
                if float_is_zero(quantity, precision_rounding=move.product_uom.rounding):
                    move._action_cancel()
                    continue

                if float_compare(move.product_uom_qty, quantity, precision_rounding=move.product_uom.rounding):
                    should_reassign = move.state == "assigned"
                    move._do_unreserve()
                    move.product_uom_qty = quantity
                    if should_reassign:
                        move._action_assign()

    @api.depends('group_id', 'move_ids', 'origin')
    def _compute_mrp_production_ids(self):
        super()._compute_mrp_production_ids()
        for picking in self:
            if not picking.origin:
                continue
            mo_names = re.findall(r"\b(?:GMP|M-WH|WH)/MO[A-Z]*/\d+\b", picking.origin)
            if not mo_names:
                continue
            additional_mos = self.env['mrp.production'].search([
                ('name', 'in', mo_names),
            ])
            if additional_mos:
                picking.production_ids = picking.production_ids | additional_mos
                picking.production_count = len(picking.production_ids)
