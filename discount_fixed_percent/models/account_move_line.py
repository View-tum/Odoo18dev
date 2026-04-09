from odoo import models, fields, api
from odoo.exceptions import ValidationError


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

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

    @api.depends("price_unit", "quantity", "discount")
    def _compute_hidden_discount_amount(self):
        for line in self:
            total_price = line.price_unit * line.quantity
            line.hidden_discount_amount = (total_price * line.discount) / 100

    @api.onchange("fixed_discount")
    def _onchange_fixed_discount(self):
        """
        Triggered when the 'Fixed Discount' field is modified.

        Action:
            1. Calculates the percentage discount based on the total line price (price_unit * quantity).
            2. Updates the standard Odoo 'discount' field with the calculated percentage.
            3. Resets 'percent_discount' to 0.0 to avoid conflict between fixed and percentage modes.
        """

        for line in self:
            if line.fixed_discount:
                total_price = line.price_unit * line.quantity
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
        Triggered when the 'Percentage Discount' field is modified.

        Action:
            1. Updates the standard Odoo 'discount' field with the entered percentage.
            2. Resets 'fixed_discount' to 0.0 to ensure only one discount mode is active.
        """

        for line in self:
            if line.percent_discount:
                line.discount = line.percent_discount
                line.fixed_discount = 0.0
            else:
                if line.fixed_discount == 0:
                    line.discount = 0.0

    @api.onchange("quantity", "price_unit")
    def _onchange_quantity_price_update_fixed_discount(self):
        """
        Triggered when 'Quantity' or 'Price Unit' is modified.

        Action:
            Recalculates the 'Fixed Discount' amount based on the existing percentage discount (line.discount).
            This ensures that the fixed discount amount remains consistent with the new total line price.
        """

        for line in self:
            total_price = line.price_unit * line.quantity
            if line.discount:
                line.fixed_discount = (total_price * line.discount) / 100

    @api.onchange("fixed_discount", "percent_discount", "quantity", "price_unit")
    def _check_discount_validity(self):
        for line in self:
            if line.display_type in ("line_section", "line_note"):
                continue

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

            total_price = line.quantity * line.price_unit
            if line.fixed_discount > total_price:
                line.fixed_discount = 0
                return {
                    "warning": {
                        "title": "ค่าไม่ถูกต้อง",
                        "message": "ส่วนลดจำนวนเงิน (Fixed Discount) ห้ามเกินมูลค่ารวมของรายการ (%.2f) ระบบได้รีเซ็ตค่าเป็น 0 แล้ว"
                        % total_price,
                    }
                }
