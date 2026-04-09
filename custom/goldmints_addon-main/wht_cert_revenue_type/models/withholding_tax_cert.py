from odoo import models

class WithholdingTaxCert(models.Model):
    _inherit = "withholding.tax.cert"

    def _compute_desc_type_other(self, lines, ttype, income_type):
        """
        เขียนทับฟังก์ชันของ l10n_th_account_wht_cert_form 
        เพื่อบังคับให้ PDF Report ดึงค่าจาก Field ใหม่ที่เราสร้างขึ้น
        """
        # หาก Report พยายามดึงฟิลด์ 'wht_cert_income_desc' ให้สลับไปดึง 'revenue_type_id.name' แทน
        if ttype == 'wht_cert_income_desc':
            ttype = 'revenue_type_id.name'
            
        # เรียกใช้การทำงานเดิมของโมดูลหลัก แต่ส่งพารามิเตอร์ใหม่ไปให้
        return super(WithholdingTaxCert, self)._compute_desc_type_other(lines, ttype, income_type)