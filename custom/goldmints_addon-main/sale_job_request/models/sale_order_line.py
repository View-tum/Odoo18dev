from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    jr_note = fields.Text(string="Notes", copy=False)
    jr_line_number = fields.Integer(string="#", compute="_compute_jr_line_number", store=False)

    @api.depends("sequence", "order_id.order_line")
    def _compute_jr_line_number(self):
        for line in self:
            if not line.order_id:
                line.jr_line_number = 0
                continue
            # ใช้ sorted() โดยไม่ระบุ key เพื่อให้ Odoo ใช้ _order (sequence, id) 
            # ซึ่งรองรับ NewId (Virtual ID) ได้ถูกต้องใน Odoo 17/18
            ordered = line.order_id.order_line.sorted()
            # 1-based index
            index = 0
            for idx, l in enumerate(ordered, start=1):
                if l.id == line.id:
                    index = idx
                    break
            line.jr_line_number = index

    @api.constrains("jr_note")
    def _check_jr_note_length(self):
        for line in self:
            if line.jr_note and len(line.jr_note) > 500:
                raise ValidationError("Note length must be 500 characters or fewer.")
