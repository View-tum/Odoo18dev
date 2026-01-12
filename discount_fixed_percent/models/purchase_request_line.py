from odoo import models, fields, api
from odoo.exceptions import ValidationError


class PurchaseRequestLine(models.Model):
    _inherit = "purchase.request.line"

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
    sequence = fields.Integer(
        string="Sequence",
        default=10,
        help="Technical sequence used in inherited views; added for compatibility.",
    )
    hidden_discount_amount = fields.Float(
        string="Hidden Discount Amount",
        compute="_compute_hidden_discount_amount",
        store=True,
        digits=(16, 2),
    )

    @api.depends("unit_cost", "product_qty", "discount")
    def _compute_hidden_discount_amount(self):
        for line in self:
            total_price = line.unit_cost * line.product_qty
            line.hidden_discount_amount = (total_price * line.discount) / 100

    @api.onchange("fixed_discount")
    def _onchange_fixed_discount(self):
        """
        Triggered when 'Fixed Discount' changes on the Purchase Request line.

        Action:
            Calculates the percentage discount based on unit cost and quantity.
            Resets 'percent_discount' to avoid ambiguity.
        """

        for line in self:
            if line.fixed_discount:
                total_price = line.unit_cost * line.product_qty
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
        Triggered when 'Percentage Discount' changes on the Purchase Request line.

        Action:
            Applies the percentage to the standard discount field and clears the fixed discount amount.
        """

        for line in self:
            if line.percent_discount:
                line.discount = line.percent_discount
                line.fixed_discount = 0.0
            else:
                if line.fixed_discount == 0:
                    line.discount = 0.0

    @api.onchange("product_qty", "unit_cost")
    def _onchange_quantity_cost_update_fixed_discount(self):
        """
        Triggered when 'Quantity' or 'Unit Cost' changes.

        Action:
            Recalculates the 'Fixed Discount' amount to match the existing discount percentage
            applied to the new total estimated cost.
        """

        for line in self:
            total_price = line.unit_cost * line.product_qty
            if line.discount:
                line.fixed_discount = (total_price * line.discount) / 100

    @api.onchange("fixed_discount", "percent_discount", "product_qty", "unit_cost")
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

            total_price = line.product_qty * line.unit_cost
            if line.fixed_discount > total_price:
                line.fixed_discount = 0
                return {
                    "warning": {
                        "title": "ค่าไม่ถูกต้อง",
                        "message": "ส่วนลดจำนวนเงิน (Fixed Discount) ห้ามเกินมูลค่ารวมของรายการ (%.2f) ระบบได้รีเซ็ตค่าเป็น 0 แล้ว"
                        % total_price,
                    }
                }
