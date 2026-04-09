from odoo import api, fields, models


class ClaimLineLotEpt(models.Model):
    _name = "claim.line.lot.ept"
    _description = "RMA Claim Line Lot Breakdown"

    claim_line_id = fields.Many2one(
        "claim.line.ept",
        string="Claim Line",
        required=True,
        ondelete="cascade",
    )
    lot_id = fields.Many2one(
        "stock.lot",
        string="Lot/Serial",
        required=True,
    )
    quantity = fields.Float(
        string="Quantity",
        required=True,
        default=1.0,
    )
    uom_id = fields.Many2one(
        "uom.uom",
        string="UoM",
        required=True,
    )
    unit_cost = fields.Float(
        string="Unit Cost (FIFO)",
        compute="_compute_unit_cost",
        store=True,
        digits="Product Price",
    )
    subtotal_cost = fields.Float(
        string="Subtotal",
        compute="_compute_subtotal",
        store=True,
        digits="Product Price",
    )
    quantity_in_base_uom = fields.Float(
        string="Qty (Base UoM)",
        compute="_compute_quantity_in_base_uom",
        store=True,
        digits="Product Unit of Measure",
    )

    @api.depends("lot_id", "claim_line_id.product_id")
    def _compute_unit_cost(self):
        for line in self:
            if not line.lot_id or not line.claim_line_id.product_id:
                line.unit_cost = 0.0
                continue

            product = line.claim_line_id.product_id
            company_id = (
                line.claim_line_id.claim_id.company_id.id
                if line.claim_line_id.claim_id
                else self.env.company.id
            )

            layer = self.env["stock.valuation.layer"].search(
                [
                    ("product_id", "=", product.id),
                    ("lot_id", "=", line.lot_id.id),
                    ("company_id", "=", company_id),
                    ("remaining_qty", ">", 0),
                ],
                order="create_date asc",
                limit=1,
            )

            if layer:
                line.unit_cost = layer.unit_cost
            else:
                line.unit_cost = product.standard_price

    @api.depends("quantity", "uom_id", "claim_line_id.product_id")
    def _compute_quantity_in_base_uom(self):
        for line in self:
            if not line.uom_id or not line.claim_line_id.product_id:
                line.quantity_in_base_uom = line.quantity
                continue

            base_uom = line.claim_line_id.product_id.uom_id
            line.quantity_in_base_uom = line.uom_id._compute_quantity(
                line.quantity, base_uom
            )

    @api.depends("quantity_in_base_uom", "unit_cost")
    def _compute_subtotal(self):
        for line in self:
            line.subtotal_cost = line.quantity_in_base_uom * line.unit_cost

    @api.onchange("lot_id")
    def _onchange_lot_id(self):
        if self.lot_id and self.claim_line_id.product_id:
            self.uom_id = self.claim_line_id.product_id.uom_id
