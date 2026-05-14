from odoo import api, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _get_sale_delivery_pickings(self):
        """Return pickings that belong to the sale delivery flow.

        Manufacturing transfer pickings can share the sale procurement group for
        merge/traceability. They should not appear in the Sale Order Delivery
        smart button unless they are directly created by the sale flow.
        """
        self.ensure_one()
        return self.picking_ids.filtered(
            lambda picking: (
                picking.origin == self.name
                or picking.location_dest_id.usage == "customer"
                or any(
                    move.sale_line_id.order_id == self
                    for move in picking.move_ids_without_package
                )
            )
        )

    @api.depends(
        "picking_ids",
        "picking_ids.origin",
        "picking_ids.location_dest_id",
        "picking_ids.move_ids_without_package.sale_line_id",
    )
    def _compute_picking_ids(self):
        for order in self:
            order.delivery_count = len(order._get_sale_delivery_pickings())

    @api.depends(
        "picking_ids",
        "picking_ids.state",
        "picking_ids.origin",
        "picking_ids.location_dest_id",
        "picking_ids.move_ids_without_package.sale_line_id",
    )
    def _compute_delivery_status(self):
        for order in self:
            pickings = order._get_sale_delivery_pickings()
            if not pickings or all(picking.state == "cancel" for picking in pickings):
                order.delivery_status = False
            elif all(picking.state in ["done", "cancel"] for picking in pickings):
                order.delivery_status = "full"
            elif any(picking.state == "done" for picking in pickings) and any(
                line.qty_delivered for line in order.order_line
            ):
                order.delivery_status = "partial"
            elif any(picking.state == "done" for picking in pickings):
                order.delivery_status = "started"
            else:
                order.delivery_status = "pending"

    def action_view_delivery(self):
        self.ensure_one()
        pickings = self._get_sale_delivery_pickings()
        if pickings:
            return self._get_action_view_picking(pickings)

        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_picking_tree_all")
        action["domain"] = [("id", "=", False)]
        action["context"] = {
            "default_partner_id": self.partner_id.id,
            "default_origin": self.name,
            "default_group_id": self.procurement_group_id.id,
        }
        return action
