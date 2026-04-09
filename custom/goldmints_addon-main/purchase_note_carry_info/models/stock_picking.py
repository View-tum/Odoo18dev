from odoo import api, fields, models

class StockPicking(models.Model):
    _inherit = "stock.picking"

    purchase_note = fields.Text(
        string="Purchase Note",
        compute="_compute_purchase_note",
        store=True,
        readonly=True,
        help="(365 custom) Note carried from the related Purchase Order (readonly)."
    )


    sequence_code = fields.Char(
        related='picking_type_id.sequence_code',
        help="(365 custom) Technical sequence code of the operation type."
    )

    @api.depends(
        "move_ids.purchase_line_id.order_id.purchase_note",
        "origin"
    )
    def _compute_purchase_note(self):
        for picking in self:
            note = False
            pos_from_moves = picking.move_ids.mapped("purchase_line_id.order_id")
            if pos_from_moves:
                note = pos_from_moves[0].purchase_note
            elif picking.origin:
                po_from_origin = self.env["purchase.order"].search(
                    [("name", "=", picking.origin)], limit=1
                )
                if po_from_origin:
                    note = po_from_origin.purchase_note
            picking.purchase_note = note