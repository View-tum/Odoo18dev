from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    fixed_discount = fields.Float(
        string="Disc.(AMT)",
        digits=(16, 2),
        help="(365 custom) ส่วนลดแบบจำนวนเงิน (บาท)",
    )
    percent_discount = fields.Float(
        string="Disc.(%)",
        digits=(16, 2),
        help="(365 custom) ส่วนลดแบบเปอร์เซ็นต์ (%)",
    )
    hidden_discount_amount = fields.Float(
        string="Hidden Discount Amount",
        compute="_compute_hidden_discount_amount",
        store=True,
        digits=(16, 2),
    )

    discount = fields.Float(
        string="Discount (%)",
        compute="_compute_discount",
        digits=(16, 2),
        store=True,
        readonly=False,
        precompute=True,
    )

    # @api.depends('product_id', 'product_uom', 'product_uom_qty')
    # def _compute_percent_discount(self):
    #     discount_enabled = self.env['product.pricelist.item']._is_discount_feature_enabled()
    #     for line in self:
    #         if not line.product_id or line.display_type:
    #             line.percent_discount = 0.0
    #
    #         if not (line.order_id.pricelist_id and discount_enabled):
    #             continue
    #
    #         if line.combo_item_id:
    #             line.percent_discount = line._get_linked_line().percent_discount
    #             continue
    #
    #         line.percent_discount = 0.0
    #
    #         if not line.pricelist_item_id._show_discount():
    #             # No pricelist rule was found for the product
    #             # therefore, the pricelist didn't apply any discount/change
    #             # to the existing sales price.
    #             continue
    #
    #         line = line.with_company(line.company_id)
    #         pricelist_price = line._get_pricelist_price()
    #         base_price = line._get_pricelist_price_before_discount()
    #
    #         if base_price != 0:  # Avoid division by zero
    #             percent_discount = (base_price - pricelist_price) / base_price * 100
    #             if (percent_discount > 0 and base_price > 0) or (percent_discount < 0 and base_price < 0):
    #                 # only show negative discounts if price is negative
    #                 # otherwise it's a surcharge which shouldn't be shown to the customer
    #                 line.percent_discount = percent_discount

    @api.depends("price_unit", "product_uom_qty", "discount")
    def _compute_hidden_discount_amount(self):
        for line in self:
            total_price = line.price_unit * line.product_uom_qty
            line.hidden_discount_amount = (total_price * line.discount) / 100

    # @api.onchange("fixed_discount")
    # def _onchange_fixed_discount(self):
    #     """
    #     Triggered when the 'Fixed Discount' field is modified.

    #     Action:
    #         Calculates the equivalent percentage discount based on the total line price
    #         and updates the standard 'discount' field. Resets 'percent_discount' to 0.
    #     """

    #     for line in self:
    #         if line.fixed_discount:
    #             total_price = line.price_unit * line.product_uom_qty
    #             if total_price != 0:
    #                 line.discount = (line.fixed_discount / total_price) * 100
    #             else:
    #                 line.discount = 0.0
    #             line.percent_discount = 0.0
    #         else:
    #             if line.percent_discount == 0:
    #                 line.discount = 0.0

    # @api.onchange("percent_discount")
    # def _onchange_percent_discount(self):
    #     """
    #     Triggered when the 'Percentage Discount' field is modified.

    #     Action:
    #         Updates the standard 'discount' field with the given percentage
    #         and resets 'fixed_discount' to 0.
    #     """

    #     for line in self:
    #         if line.percent_discount:
    #             line.discount = line.percent_discount
    #             line.fixed_discount = 0.0
    #         else:
    #             if line.fixed_discount == 0:
    #                 line.discount = 0.0

    # @api.onchange("product_uom_qty", "price_unit")
    # def _onchange_quantity_price_update_fixed_discount(self):
    #     """
    #     Triggered when 'Quantity' or 'Price Unit' changes.

    #     Action:
    #         Recalculates the 'Fixed Discount' value based on the current percentage discount.
    #         This keeps the fixed amount value synchronized with the updated line total.
    #     """

    #     for line in self:
    #         total_price = line.price_unit * line.product_uom_qty
    #         if line.discount:
    #             line.fixed_discount = (total_price * line.discount) / 100

    def _prepare_invoice_line(self, **optional_values):
        """
        Prepares the dictionary of values to create a new invoice line from this sale order line.

        Override:
            - Calculates the proportional 'fixed_discount' based on the quantity actually being invoiced (partial invoicing).
            - Transfers the 'percent_discount' value to the invoice line.
        """

        res = super(SaleOrderLine, self)._prepare_invoice_line(**optional_values)
        quantity = optional_values.get("quantity") or self.qty_to_invoice

        if self.product_uom_qty:
            ratio = quantity / self.product_uom_qty

        # if self.fixed_discount:
        #     res["fixed_discount"] = self.fixed_discount * ratio
        # else:
        res["fixed_discount"] = 0.0

        if self.hidden_discount_amount:
            res["hidden_discount_amount"] = self.hidden_discount_amount * ratio
        else:
            res["hidden_discount_amount"] = 0.0

        # res["percent_discount"] = self.percent_discount
        res["percent_discount"] = self.discount
        return res

    # @api.onchange("fixed_discount", "percent_discount", "product_uom_qty", "price_unit")
    # def _check_discount_validity(self):
    #     for line in self:
    #         if line.fixed_discount < 0 or line.percent_discount < 0:
    #             line.fixed_discount = 0
    #             line.percent_discount = 0
    #             return {
    #                 "warning": {
    #                     "title": "ค่าไม่ถูกต้อง",
    #                     "message": "ส่วนลด (จำนวนเงิน หรือ %) ห้ามมีค่าติดลบ ระบบได้รีเซ็ตค่าเป็น 0 แล้ว",
    #                 }
    #             }

    #         if line.percent_discount > 100:
    #             line.percent_discount = 100
    #             return {
    #                 "warning": {
    #                     "title": "ค่าไม่ถูกต้อง",
    #                     "message": "ส่วนลดเปอร์เซ็นต์ห้ามเกิน 100% ระบบได้ปรับค่าเป็น 100% แล้ว",
    #                 }
    #             }

    #         total_price = line.product_uom_qty * line.price_unit
    #         if line.fixed_discount > total_price:
    #             line.fixed_discount = 0
    #             return {
    #                 "warning": {
    #                     "title": "ค่าไม่ถูกต้อง",
    #                     "message": "ส่วนลดจำนวนเงิน (Fixed Discount) ห้ามเกินมูลค่ารวมของรายการ (%.2f) ระบบได้รีเซ็ตค่าเป็น 0 แล้ว"
    #                     % total_price,
    #                 }
    #             }
