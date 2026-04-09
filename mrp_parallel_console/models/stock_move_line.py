from odoo import api, fields, models

class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    qty_on_hand_show = fields.Float(
        string="On Hand",
        compute="_compute_qty_on_hand_show",
        store=False
    )

    @api.depends("product_id", "location_id", "lot_id")
    def _compute_qty_on_hand_show(self):
        for line in self:
            if not line.product_id or not line.location_id:
                line.qty_on_hand_show = 0.0
                continue

            domain = [
                ("product_id", "=", line.product_id.id),
                ("location_id", "=", line.location_id.id),
            ]
            if line.lot_id:
                domain.append(("lot_id", "=", line.lot_id.id))

            quants = self.env["stock.quant"].sudo().search(domain)
            line.qty_on_hand_show = sum(quants.mapped("quantity"))

    @api.onchange("location_id", "product_id")
    def _onchange_location_auto_lot(self):
        # 1) Default location from the first line (if any) when this line has no explicit location
        if self.move_id and self.move_id.move_line_ids:
            first_line = self.move_id.move_line_ids[0]
            if first_line.location_id and first_line != self:
                if not self.location_id or self.location_id == self.move_id.location_id:
                    self.location_id = first_line.location_id

        if not self.location_id or not self.product_id:
            return

        # 2) Auto-select Lot (FIFO) and fill only the remaining demand of the move
        if self.product_id.tracking in ("lot", "serial") and not self.lot_id:
            quant = self.env["stock.quant"].sudo().search(
                [
                    ("product_id", "=", self.product_id.id),
                    ("location_id", "child_of", self.location_id.id),
                    ("quantity", ">", 0),
                    ("lot_id", "!=", False),
                ],
                limit=1,
                order="in_date, id",
            )

            if not quant:
                return

            self.lot_id = quant.lot_id

            move = self.move_id
            fill_qty = quant.quantity
            if move and move.product_uom_qty:
                required = move.product_uom_qty
                already = 0.0
                for line in move.move_line_ids:
                    if line == self:
                        continue
                    if "quantity" in line._fields:
                        already += line.quantity or 0.0
                    else:
                        already += line.qty_done or 0.0

                remaining = max(required - already, 0.0)
                if remaining > 0:
                    fill_qty = min(quant.quantity, remaining)
                else:
                    fill_qty = 0.0

            if "quantity" in self._fields:
                self.quantity = fill_qty
            else:
                self.qty_done = fill_qty
