from odoo import models, fields, api


class VendorAdd(models.Model):
    _inherit = "purchase.request"

    # Allow only partners marked as vendors (supplier_rank > 0)
    vendor = fields.Many2one(
        'res.partner',
        string="Vendor",
        required=False,
        domain=[('supplier_rank', '>', 0)],
    )

    vendor_currency_id = fields.Many2one(
        'res.currency',
        string='Vendor Currency',
        compute='_compute_vendor_currency',
        store=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        related='vendor_currency_id',
        store=True,
        readonly=True,
    )

    @api.depends('vendor')
    def _compute_vendor_currency(self):
        for rec in self:
            currency = False
            if rec.vendor:
                currency = rec.vendor.property_purchase_currency_id
            rec.vendor_currency_id = currency or rec.company_id.currency_id


class UnitPrice(models.Model):
    _inherit = "purchase.request.line"

    unit_cost = fields.Float(string='Unit cost', required=True)

    @api.depends('request_id')
    def _compute_vendor(self):
        """ อัปเดต vendor อัตโนมัติจาก request_id """
        for rec in self:
            rec.vendor = rec.request_id.vendor if rec.request_id else False

    # Computed from request; keep same vendor-only domain for consistency
    vendor = fields.Many2one(
        'res.partner',
        string="Vendor",
        required=False,
        compute="_compute_vendor",
        store=True,
        groups="base.group_no_one",
        domain=[('supplier_rank', '>', 0)],
    )

    vendor_currency_id = fields.Many2one(
        'res.currency',
        string='Vendor Currency',
        related='request_id.vendor_currency_id',
        store=True,
        readonly=True,
    )

    company_currency_id = fields.Many2one(
        'res.currency',
        related='request_id.company_id.currency_id',
        store=True,
        readonly=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        related='vendor_currency_id',
        store=True,
        readonly=True,
    )

    unit_cost_company = fields.Monetary(
        string='Unit cost (Company)',
        currency_field='company_currency_id',
        compute='_compute_unit_cost_company',
        store=True,
        readonly=True,
    )

    estimated_cost_company = fields.Monetary(
        string='Estimated cost (Company)',
        currency_field='company_currency_id',
        compute='_compute_estimated_cost_company',
        store=True,
        readonly=True,
    )

    @api.depends('unit_cost', 'vendor_currency_id', 'request_id.company_id')
    def _compute_unit_cost_company(self):
        for rec in self:
            company = rec.request_id.company_id
            company_currency = rec.company_currency_id
            vendor_currency = rec.vendor_currency_id or company_currency
            date = fields.Date.context_today(rec)
            amount = rec.unit_cost or 0.0
            rec.unit_cost_company = vendor_currency._convert(amount, company_currency, company, date)

    @api.depends('product_qty', 'unit_cost_company')
    def _compute_estimated_cost_company(self):
        for rec in self:
            rec.estimated_cost_company = (rec.product_qty or 0.0) * (rec.unit_cost_company or 0.0)

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


