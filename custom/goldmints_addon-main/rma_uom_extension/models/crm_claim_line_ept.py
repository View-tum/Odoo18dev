from odoo import api, fields, models


class CrmClaimLineEpt(models.Model):
    _inherit = "claim.line.ept"

    product_uom_id = fields.Many2one("uom.uom", string="Unit of Measure")

    lot_line_ids = fields.One2many(
        "claim.line.lot.ept",
        "claim_line_id",
        string="Lot Breakdown",
    )

    total_lot_quantity = fields.Float(
        string="Total Qty (from Lots)",
        compute="_compute_total_from_lots",
        store=True,
        digits="Product Unit of Measure",
    )

    total_lot_cost = fields.Float(
        string="Total Cost (from Lots)",
        compute="_compute_total_from_lots",
        store=True,
        digits="Product Price",
    )

    cost_per_piece = fields.Float(
        string="Cost per Piece (FIFO)",
        compute="_compute_fifo_cost",
        store=True,
        digits="Product Price",
        help="Derived average cost per piece from the original stock move.",
    )

    price_unit = fields.Float(
        string="Refund Price",
        compute="_compute_price_unit",
        readonly=False,
        store=True,
        digits="Product Price",
    )

    @api.depends("lot_line_ids.quantity_in_base_uom", "lot_line_ids.subtotal_cost")
    def _compute_total_from_lots(self):
        for line in self:
            line.total_lot_quantity = sum(line.lot_line_ids.mapped("quantity_in_base_uom"))
            line.total_lot_cost = sum(line.lot_line_ids.mapped("subtotal_cost"))


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "product_id" in vals and not vals.get("product_uom_id"):
                product = self.env["product.product"].browse(vals["product_id"])
                vals["product_uom_id"] = product.uom_id.id
        return super().create(vals_list)

    @api.depends("move_id", "product_id", "serial_lot_ids")
    def _compute_fifo_cost(self):
        for line in self:
            if not line.product_id:
                line.cost_per_piece = 0.0
                continue

            base_cost = 0.0

            if line.move_id and line.move_id.price_unit:
                move_price_unit = abs(line.move_id.price_unit)
                if line.move_id.product_uom != line.product_id.uom_id:
                    base_cost = line.move_id.product_uom._compute_price(
                        move_price_unit, line.product_id.uom_id
                    )
                else:
                    base_cost = move_price_unit

            if not base_cost and line.serial_lot_ids:
                company_id = line.claim_id.company_id.id if line.claim_id else self.env.company.id
                layer = self.env['stock.valuation.layer'].search([
                    ('product_id', '=', line.product_id.id),
                    ('lot_id', 'in', line.serial_lot_ids.ids),
                    ('company_id', '=', company_id),
                    ('remaining_qty', '>', 0),
                ], order='create_date asc', limit=1)
                if layer:
                    base_cost = layer.unit_cost

            if not base_cost:
                base_cost = line.product_id.standard_price

            line.cost_per_piece = base_cost

    @api.depends("cost_per_piece", "product_uom_id")
    def _compute_price_unit(self):
        """
        Scale the per-piece cost to the selected Unit of Measure.
        """
        for line in self:
            if not line.product_uom_id or not line.product_id:
                line.price_unit = 0.0
                continue

            qty_in_ref = line.product_uom_id._compute_quantity(1.0, line.product_id.uom_id)
            line.price_unit = line.cost_per_piece * qty_in_ref

    @api.onchange("product_id")
    def onchange_product_set_uom(self):
        if self.product_id and not self.product_uom_id:
            self.product_uom_id = self.product_id.uom_id
