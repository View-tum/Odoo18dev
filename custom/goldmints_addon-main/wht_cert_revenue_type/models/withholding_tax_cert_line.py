from odoo import models, fields, api

class WithholdingTaxCertLine(models.Model):
    _inherit = 'withholding.tax.cert.line'
    
    # เขียนทับฟิลด์เดิม เพื่อปลดล็อค readonly ในระดับ ORM และให้เซฟลง Database ได้
    wht_percent = fields.Float(
        string='% Tax', 
        readonly=False, 
        store=True,
        compute=False # ใส่ไว้เพื่อตัดการผูก Compute เดิม (ถ้ามี) จากโมดูลแม่
    )

    revenue_type_id = fields.Many2one(
        'wht.revenue.type', 
        string='Income Description'
    )

    @api.onchange('revenue_type_id')
    def _onchange_revenue_type_id(self):
        """เมื่อเลือกประเภทรายได้ ให้เติม Description และ WHT Rate ลงในฟิลด์เดิมอัตโนมัติ และคำนวณภาษี"""
        for rec in self:
            if rec.revenue_type_id:
                rec.wht_cert_income_desc = rec.revenue_type_id.name
                rec.wht_percent = rec.revenue_type_id.wht_rate
                
                # คำนวณ Tax Amount ทันทีเมื่อเปลี่ยนประเภทรายได้
                rec.amount = (rec.base * rec.wht_percent) / 100.0

    @api.onchange('wht_percent', 'base')
    def _onchange_calculate_tax_amount(self):
        """คำนวณ Tax Amount ใหม่เมื่อมีการแก้ไข % Tax หรือ Base Amount"""
        for rec in self:
            rec.amount = (rec.base * rec.wht_percent) / 100.0