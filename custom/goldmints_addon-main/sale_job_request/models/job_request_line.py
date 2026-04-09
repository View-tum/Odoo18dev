from odoo import api, fields, models


class JobRequestLine(models.Model):
    _name = "job.request.line"
    _description = "Job Request Line"
    _order = "sequence, id"

    job_id = fields.Many2one("job.request", string="Job Request", ondelete="cascade", required=True)
    sequence = fields.Integer(default=10)
    product_id = fields.Many2one("product.product", string="Product", required=True)
    name = fields.Text(string="Description", required=True)
    product_uom_qty = fields.Float(string="Quantity", default=1.0, digits="Product Unit of Measure")
    product_uom = fields.Many2one("uom.uom", string="Unit of Measure")
    jr_note = fields.Text(string="Notes")
    jr_line_number = fields.Integer(string="#", compute="_compute_jr_line_number")

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.get_product_multiline_description_sale()
            self.product_uom = self.product_id.uom_id

    @api.depends("sequence", "job_id.jr_line_ids")
    def _compute_jr_line_number(self):
        for line in self:
            if not line.job_id:
                line.jr_line_number = 0
                continue
            # ใช้ sorted() โดยไม่ระบุ key เพื่อให้ Odoo ใช้ _order (sequence, id) 
            # ซึ่งรองรับ NewId (Virtual ID) ได้ถูกต้องใน Odoo 17/18
            ordered = line.job_id.jr_line_ids.sorted()
            index = 0
            for idx, l in enumerate(ordered, start=1):
                if l._origin.id == line._origin.id or l.id == line.id:
                    index = idx
                    break
            line.jr_line_number = index
