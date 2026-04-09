# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare


class StockPicking(models.Model):
    _inherit = "stock.picking"

    can_create_late_backorder = fields.Boolean(
        compute="_compute_late_backorder_state",
        string="Can Create Late Backorder",
    )
    late_backorder_move_count = fields.Integer(
        compute="_compute_late_backorder_state",
        string="Late Backorder Lines",
    )

    @staticmethod
    def _get_late_backorder_move_rounding(move):
        rounding = (
            move.product_uom.rounding
            or move.product_id.uom_id.rounding
            or 0.01
        )
        return rounding if rounding > 0 else 0.01

    def _get_late_backorder_move_specs(self):
        self.ensure_one()
        specs = []
        for move in self.move_ids.filtered(lambda m: not m.scrapped):
            if move.state == "done":
                remaining_uom_qty = max(move.product_uom_qty - move.quantity, 0.0)
            elif move.state == "cancel":
                remaining_uom_qty = move.product_uom_qty
            else:
                continue

            if float_compare(
                remaining_uom_qty,
                0.0,
                precision_rounding=self._get_late_backorder_move_rounding(move),
            ) <= 0:
                continue

            qty_product_uom = move.product_uom._compute_quantity(
                remaining_uom_qty,
                move.product_id.uom_id,
                rounding_method="HALF-UP",
            )
            specs.append((move, remaining_uom_qty, qty_product_uom))
        return specs

    @api.depends(
        "state",
        "backorder_ids",
        "move_ids.state",
        "move_ids.product_uom_qty",
        "move_ids.quantity",
        "move_ids.scrapped",
    )
    def _compute_late_backorder_state(self):
        for picking in self:
            eligible = (
                picking.state == "done"
                and not picking.backorder_ids
            )
            specs = picking._get_late_backorder_move_specs() if eligible else []
            picking.late_backorder_move_count = len(specs)
            picking.can_create_late_backorder = bool(specs)

    def action_create_late_backorder(self):
        self.ensure_one()
        if not self.can_create_late_backorder:
            raise UserError(
                _("This transfer is not eligible for late backorder creation.")
            )

        move_specs = self._get_late_backorder_move_specs()
        if not move_specs:
            raise UserError(_("There is no remaining quantity to backorder."))

        backorder_vals = {
            "picking_type_id": self.picking_type_id.id,
            "location_id": self.location_id.id,
            "location_dest_id": self.location_dest_id.id,
            "origin": self.origin,
            "company_id": self.company_id.id,
            "scheduled_date": self.scheduled_date or fields.Datetime.now(),
            "partner_id": self.partner_id.id,
        }
        
        backorder_picking = self.copy(default=backorder_vals)
        backorder_picking.move_ids.unlink()

        fallback_date = (
            backorder_picking.scheduled_date
            or self.scheduled_date
            or fields.Datetime.now()
        )
        move_vals_list = []
        for move, _remaining_uom_qty, qty_product_uom in move_specs:
            defaults = move._prepare_move_split_vals(qty_product_uom)
            defaults.update(
                {
                    "picking_id": backorder_picking.id,
                    "state": "draft",
                    "quantity": 0.0,
                    "picked": False,
                    "date": move.date or fallback_date,
                    "name": move.name,
                    "location_id": move.location_id.id,
                    "location_dest_id": move.location_dest_id.id,
                }
            )
            vals = move.copy_data(default=defaults)[0]
            vals.pop("move_line_ids", None)
            vals.pop("move_line_nosuggest_ids", None)
            vals.update(
                {
                    "picking_id": backorder_picking.id,
                    "state": "draft",
                    "quantity": 0.0,
                    "picked": False,
                }
            )
            move_vals_list.append(vals)

        backorder_moves = self.env["stock.move"].create(move_vals_list)
        backorder_moves.with_context(
            bypass_entire_pack=True,
            bypass_procurement_creation=True,
        )._action_confirm(merge=False)

        backorder_picking.user_id = False
        if backorder_picking.picking_type_id.reservation_method == "at_confirm":
            backorder_picking.action_assign()

        self.message_post(
            body=_(
                "A late backorder %s has been created after the original transfer was finished without backorder."
            )
            % backorder_picking._get_html_link()
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "stock.picking",
            "res_id": backorder_picking.id,
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "current",
        }

    def button_validate(self):
        # If we want to strictly skip the backorder wizard to allow only manual creation later
        if self.env.context.get("skip_backorder"):
            return super().button_validate()
        
        # We can add a context key here if we want to force 'No Backorder' 
        # But Odoo's standard button_validate calls the wizard if quantities are mismatched.
        # To bypass it completely and never create backorder on validate:
        return super(StockPicking, self.with_context(cancel_backorder=True)).button_validate()
