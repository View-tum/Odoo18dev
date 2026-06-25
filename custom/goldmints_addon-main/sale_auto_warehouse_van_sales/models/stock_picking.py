from odoo import api, models, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _van_sales_source_order(self):
        self.ensure_one()
        if "sale_id" in self._fields and self.sale_id:
            return self.sale_id
        return self.group_id.sale_id if self.group_id else self.env["sale.order"]

    def _van_sales_user_source_location(self, user=None):
        user = user or self.env.user
        return user.van_sale_location_id

    def _should_apply_van_sales_operation_location(self, picking_type):
        return (
            picking_type
            and picking_type.code in ("incoming", "internal", "outgoing")
            and self._van_sales_user_source_location()
            and not self.env.context.get("skip_van_sales_operation_location")
        )

    def _apply_van_sales_operation_location_vals(self, vals):
        picking_type = self.env["stock.picking.type"].browse(
            vals.get("picking_type_id") or self.env.context.get("default_picking_type_id")
        )
        if not self._should_apply_van_sales_operation_location(picking_type):
            return vals

        van_location = self._van_sales_user_source_location()
        if picking_type.code in ("internal", "outgoing"):
            default_source = picking_type.default_location_src_id
            current_source_id = vals.get("location_id")
            if not current_source_id or current_source_id == default_source.id:
                vals["location_id"] = van_location.id
        if picking_type.code == "incoming":
            default_destination = picking_type.default_location_dest_id
            current_destination_id = vals.get("location_dest_id")
            if not current_destination_id or current_destination_id == default_destination.id:
                vals["location_dest_id"] = van_location.id
        return vals

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        return self._apply_van_sales_operation_location_vals(res)

    @api.onchange("picking_type_id")
    def _onchange_van_sales_operation_location(self):
        for picking in self:
            if picking._should_apply_van_sales_operation_location(picking.picking_type_id):
                van_location = picking._van_sales_user_source_location()
                if picking.picking_type_id.code in ("internal", "outgoing"):
                    picking.location_id = van_location
                if picking.picking_type_id.code == "incoming":
                    picking.location_dest_id = van_location

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [
            self._apply_van_sales_operation_location_vals(dict(vals))
            for vals in vals_list
        ]
        pickings = super().create(vals_list)
        pickings._sync_van_sales_operation_move_locations()
        return pickings

    def write(self, vals):
        sync_locations = bool(
            {"location_id", "location_dest_id"} & set(vals)
            and not self.env.context.get("skip_van_sales_operation_location_sync")
        )
        result = super().write(vals)
        if sync_locations:
            self.with_context(skip_van_sales_operation_location_sync=True)._sync_van_sales_operation_move_locations(reassign=True)
        return result

    def web_read(self, specification):
        self._sync_van_sales_operation_move_locations(reassign=True)
        return super().web_read(specification)

    def _van_sales_operation_move_location_vals(self):
        self.ensure_one()
        if self.picking_type_id.code in ("internal", "outgoing") and self.location_id:
            return {"location_id": self.location_id.id}
        if self.picking_type_id.code == "incoming" and self.location_dest_id:
            return {"location_dest_id": self.location_dest_id.id}
        return {}

    def _has_van_sales_operation_location(self):
        self.ensure_one()
        location = self.location_dest_id if self.picking_type_id.code == "incoming" else self.location_id
        if not location:
            return False
        if "CARSALE" in (location.complete_name or location.name or "").upper():
            return True
        return bool(self.env["res.users"].sudo().search_count([("van_sale_location_id", "=", location.id)], limit=1))

    def _sync_van_sales_operation_move_locations(self, reassign=False):
        for picking in self.filtered(lambda item: item.state not in ("done", "cancel") and item._has_van_sales_operation_location()):
            vals = picking._van_sales_operation_move_location_vals()
            if not vals:
                continue
            moves = picking.move_ids.filtered(lambda move: move.state not in ("done", "cancel"))
            if not moves:
                continue
            location_field = next(iter(vals))
            target_location = self.env["stock.location"].browse(vals[location_field])
            move_lines = moves.move_line_ids
            if "state" in move_lines._fields:
                move_lines = move_lines.filtered(lambda line: line.state not in ("done", "cancel"))
            wrong_moves = moves.filtered(lambda move: move[location_field] != target_location)
            wrong_move_lines = move_lines.filtered(lambda line: line[location_field] != target_location)
            if not wrong_moves and not wrong_move_lines:
                continue
            if reassign and picking.picking_type_id.code in ("internal", "outgoing"):
                assigned_moves = moves.filtered(lambda move: move.state in ("assigned", "partially_available"))
                if assigned_moves:
                    assigned_moves._do_unreserve()
            moves.write(vals)
            move_lines = moves.move_line_ids
            if "state" in move_lines._fields:
                move_lines = move_lines.filtered(lambda line: line.state not in ("done", "cancel"))
            if move_lines:
                move_lines.write(vals)
            if reassign and picking.picking_type_id.code in ("internal", "outgoing"):
                moves.filtered(lambda move: move.state in ("confirmed", "waiting", "partially_available"))._action_assign()

    def _check_van_sales_source_location(self):
        for picking in self:
            if picking.picking_type_id.code != "outgoing":
                continue
            order = picking._van_sales_source_order()
            if not order:
                continue
            user = order.user_id
            if not user or not user.has_group("sale_auto_warehouse_van_sales.group_van_sales"):
                continue
            location = order._van_sales_target_location(user)
            if not location:
                raise UserError(_("Please set Van Sales Source Location on the salesperson before validating this delivery."))
            wrong_moves = picking.move_ids.filtered(lambda move: move.location_id != location)
            wrong_move_lines = picking.move_line_ids.filtered(lambda line: line.location_id != location)
            if picking.location_id != location or wrong_moves or wrong_move_lines:
                raise UserError(_("This van sales delivery must use %s as the source location.") % location.display_name)

    def button_validate(self):
        self._sync_van_sales_operation_move_locations(reassign=True)
        self._check_van_sales_source_location()
        return super().button_validate()
