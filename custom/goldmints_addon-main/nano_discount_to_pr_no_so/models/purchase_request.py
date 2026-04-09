from odoo import api, fields, models


class PurchaseRequestLine(models.Model):
    _inherit = "purchase.request.line"

    # Match discount controls used on purchase.order.line (nano_discount)
    discount_type = fields.Selection(
        [
            ("percentage", "Percentage"),
            ("amount", "Line Amount"),
            ("amount_per_unit", "Unit Amount"),
        ],
        default="amount",
        string="Disc.Type",
        help="Discount mode for this request line.",
    )
    discount_value = fields.Float(
        string="Discount",
        digits="Product Price",
        help="Discount value, interpreted by Disc.Type.",
    )

    # Ensure PR 'discount' percent reflects chosen type/value, so it flows to PO
    def _compute_percent_discount(self):
        """Return percent discount based on discount_type/value.

        Falls back to 0.0 when required data is missing. Does not write.
        """
        self.ensure_one()
        qty = self.product_qty or 0.0
        unit_cost = getattr(self, "unit_cost", 0.0) or 0.0
        total = qty * unit_cost
        dtype = self.discount_type or "amount"
        dval = self.discount_value or 0.0
        if dtype == "percentage":
            return dval
        if total:
            if dtype == "amount":
                return (dval * 100.0) / total
            if dtype == "amount_per_unit":
                return (dval * qty * 100.0) / total
        return 0.0
    @api.onchange("discount_type")
    def _onchange_discount_type(self):
        for line in self:
            # Update PR percent discount only if that field exists
            if "discount" in line._fields:
                line.discount = line._compute_percent_discount()
                # keep discount_value as user entered

    @api.onchange("discount_value")
    def _onchange_discount_value(self):
        for line in self:
            if "discount" in line._fields:
                line.discount = line._compute_percent_discount()


class PRLineMakePO(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.order"

    def make_purchase_order(self):
        # Run core + any other inherited logic first
        action = super().make_purchase_order()

        # Best-effort: propagate discount_type/value (and percent for safety)
        try:
            model = action.get("res_model")
            domain = action.get("domain")
            if model and domain:
                order_ids = self.env[model].search(domain).ids
            else:
                order_ids = []
        except Exception:
            order_ids = []

        if not order_ids:
            return action

        pol_model = self.env["purchase.order.line"]
        for item in self.item_ids:
            pr_line = item.line_id
            if not pr_line:
                continue
            po_lines = pol_model.search([
                ("order_id", "in", order_ids),
                ("purchase_request_lines", "in", pr_line.id),
            ])
            if not po_lines:
                continue
            vals = {}
            # Always pass percent too, in case other module isn't present
            if hasattr(pr_line, "discount"):
                vals["discount"] = pr_line.discount or 0.0
            if hasattr(pr_line, "discount_type"):
                vals["discount_type"] = pr_line.discount_type or "amount"
            if hasattr(pr_line, "discount_value"):
                vals["discount_value"] = pr_line.discount_value or 0.0
            if vals:
                po_lines.write(vals)

        return action
