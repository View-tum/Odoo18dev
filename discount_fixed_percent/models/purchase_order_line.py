from odoo import models, fields, api
from odoo.exceptions import ValidationError


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

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

    @api.depends("price_unit", "product_qty", "discount")
    def _compute_hidden_discount_amount(self):
        for line in self:
            total_price = line.price_unit * line.product_qty
            line.hidden_discount_amount = (total_price * line.discount) / 100

    @api.onchange("fixed_discount")
    def _onchange_fixed_discount(self):
        """
        Triggered when the 'Fixed Discount' field is modified on a PO line.

        Action:
            Derives the percentage discount from the fixed amount and the total line price.
            Resets the explicit 'Percentage Discount' field to zero.
        """

        for line in self:
            if line.fixed_discount:
                total_price = line.price_unit * line.product_qty
                if total_price != 0:
                    line.discount = (line.fixed_discount / total_price) * 100
                else:
                    line.discount = 0.0

                line.percent_discount = 0.0
            else:
                if line.percent_discount == 0:
                    line.discount = 0.0

    @api.onchange("percent_discount")
    def _onchange_percent_discount(self):
        """
        Triggered when the 'Percentage Discount' field is modified on a PO line.

        Action:
            Sets the standard discount field to the provided percentage and clears the fixed discount amount.
        """

        for line in self:
            if line.percent_discount:
                line.discount = line.percent_discount
                line.fixed_discount = 0.0
            else:
                if line.fixed_discount == 0:
                    line.discount = 0.0

    @api.onchange("product_qty", "price_unit")
    def _onchange_quantity_price_update_fixed_discount(self):
        """
        Triggered when 'Quantity' or 'Unit Price' is updated.

        Action:
            Updates the 'Fixed Discount' amount by recalculating it from the current discount percentage
            and the new total price.
        """

        for line in self:
            total_price = line.price_unit * line.product_qty
            if line.discount:
                line.fixed_discount = (total_price * line.discount) / 100

    def _prepare_account_move_line(self, move=False):
        """
        Prepares the dictionary of values to create a vendor bill line from this PO line.

        Override:
            - Calculates 'fixed_discount' proportionally based on the 'qty_to_bill' (partial billing).
            - Passes the 'percent_discount' to the move line.
        """

        res = super(PurchaseOrderLine, self)._prepare_account_move_line(move=move)
        qty_to_bill = res.get("quantity", 0.0)
        ratio = 0.0

        if self.product_qty and qty_to_bill:
            ratio = qty_to_bill / self.product_qty

        if self.fixed_discount:
            res["fixed_discount"] = self.fixed_discount * ratio
        else:
            res["fixed_discount"] = 0.0

        if self.hidden_discount_amount:
            res["hidden_discount_amount"] = self.hidden_discount_amount * ratio
        else:
            res["hidden_discount_amount"] = 0.0

        res["percent_discount"] = self.percent_discount
        return res

    @api.onchange("fixed_discount", "percent_discount", "product_qty", "price_unit")
    def _check_discount_validity(self):
        for line in self:
            if line.fixed_discount < 0 or line.percent_discount < 0:
                line.fixed_discount = 0
                line.percent_discount = 0
                return {
                    "warning": {
                        "title": "ค่าไม่ถูกต้อง",
                        "message": "ส่วนลด (จำนวนเงิน หรือ %) ห้ามมีค่าติดลบ ระบบได้รีเซ็ตค่าเป็น 0 แล้ว",
                    }
                }

            if line.percent_discount > 100:
                line.percent_discount = 100
                return {
                    "warning": {
                        "title": "ค่าไม่ถูกต้อง",
                        "message": "ส่วนลดเปอร์เซ็นต์ห้ามเกิน 100% ระบบได้ปรับค่าเป็น 100% แล้ว",
                    }
                }

            total_price = line.product_qty * line.price_unit
            if line.fixed_discount > total_price:
                line.fixed_discount = 0
                return {
                    "warning": {
                        "title": "ค่าไม่ถูกต้อง",
                        "message": "ส่วนลดจำนวนเงิน (Fixed Discount) ห้ามเกินมูลค่ารวมของรายการ (%.2f) ระบบได้รีเซ็ตค่าเป็น 0 แล้ว"
                        % total_price,
                    }
                }
