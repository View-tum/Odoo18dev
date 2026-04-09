from odoo import models, fields

class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    invoice_date = fields.Date(
        string='Invoice Date',
        default=fields.Date.context_today,
        help="ระบุวันที่ที่ต้องการให้แสดงบน Invoice หากไม่ระบุ ระบบจะจัดการตามมาตรฐาน"
    )

    def create_invoices(self):
        self.ensure_one()
        if self.invoice_date:
            self = self.with_context(force_wizard_invoice_date=self.invoice_date)
            
        return super(SaleAdvancePaymentInv, self).create_invoices()