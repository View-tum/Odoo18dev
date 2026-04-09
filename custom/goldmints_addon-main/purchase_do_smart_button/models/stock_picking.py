from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    # Internal helper fields
    show_po_button = fields.Boolean(
        string="Show PO Button",
        compute="_compute_show_po_button",
        store=False,
        help="(365 custom) Technical field to control the visibility of the 'Purchase Order' button. \
            The button is shown for incoming picking types or related operations (e.g., QC, STOR)."
    )

    po_ids = fields.Many2many(
        comodel_name="purchase.order",
        compute="_compute_po_links",
        string="Purchase Orders",
        store=False,
        help="(365 custom) All Purchase Orders related to this stock picking, computed automatically by tracing back to the source documents."
    )
    po_count = fields.Integer(
        compute="_compute_po_links",
        string="PO Count",
        store=False,
        help="(365 custom) The number of Purchase Orders linked to this stock picking."
    )

    @api.depends(
        "move_ids_without_package",
        "move_ids_without_package.purchase_line_id",
        "move_ids_without_package.move_orig_ids",
        "move_ids_without_package.move_orig_ids.purchase_line_id",
        "picking_type_id",
    )
    def _compute_po_links(self):
        for picking in self:
            # Start from this picking's moves and walk up the origins to capture
            # upstream moves (e.g., QC/STOR steps chained from the incoming).
            moves = picking.move_ids_without_package
            all_moves = moves
            for _depth in range(3):
                origin_moves = all_moves.mapped("move_orig_ids").exists()
                new_moves = origin_moves - all_moves
                if not new_moves:
                    break
                all_moves |= new_moves

            orders = all_moves.mapped("purchase_line_id.order_id").exists()
            picking.po_ids = orders
            picking.po_count = len(orders)

    @api.depends("picking_type_code", "picking_type_id.sequence_code")
    def _compute_show_po_button(self):
        for picking in self:
            seq = picking.picking_type_id.sequence_code
            picking.show_po_button = picking.picking_type_code == "incoming" or (
                seq in ("QC", "STOR")
            )

    def action_view_pos(self):
        self.ensure_one()
        action = {
            "type": "ir.actions.act_window",
            "name": "Purchase Orders",
            "res_model": "purchase.order",
            "view_mode": "list,form",
            "domain": [("id", "in", self.po_ids.ids)],
            "target": "current",
        }
        if self.po_count == 1:
            action.update({"view_mode": "form", "res_id": self.po_ids.id})
        return action
