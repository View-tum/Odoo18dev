from odoo import models, fields, api


class VendorAdd(models.Model):
    _inherit = "purchase.request"

    vendor = fields.Many2one('res.partner', string="Vendor", required=False)


class UnitPrice(models.Model):
    _inherit = "purchase.request.line"

    unit_cost = fields.Float(string='Unit cost', required=True)

    @api.depends('request_id')
    def _compute_vendor(self):
        """ อัปเดต vendor อัตโนมัติจาก request_id """
        for rec in self:
            rec.vendor = rec.request_id.vendor if rec.request_id else False

    vendor = fields.Many2one('res.partner', string="Vendor", required=False, compute="_compute_vendor", store=True)

    @api.onchange('unit_cost', 'product_qty')
    def unit_cost_add(self):
        for rec in self:
            rec.estimated_cost = rec.product_qty * rec.unit_cost

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """ ดึง vendor และ unit_cost จาก product.supplierinfo ที่มี ID มากที่สุด """
        for rec in self:
            if rec.product_id:
                supplier_info = self.env['product.supplierinfo'].search([
                    ('product_tmpl_id', '=', rec.product_id.product_tmpl_id.id)
                ], limit=1, order="id DESC")  # ดึง supplierinfo ที่มี ID มากที่สุด
                if supplier_info:
                    # rec.vendor = supplier_info.partner_id  # ใช้ partner_id แทน name
                    rec.unit_cost = supplier_info.price  # ดึงราคาจาก supplierinfo
                else:
                    # rec.vendor = False  # ล้างค่า vendor ถ้าไม่มีข้อมูล
                    rec.unit_cost = 0.0  # ตั้งค่า unit_cost เป็น 0 ถ้าไม่มีข้อมูล


