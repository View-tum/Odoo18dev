from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    # บัญชีลูกหนี้เงินยืม (Advance Account)
    # เช่น 113000 - ลูกหนี้เงินยืมทดรองจ่าย
    advance_account_id = fields.Many2one(
        "account.account",
        string="Employee Advance Account",
        domain="[('deprecated', '=', False)]",
        help="บัญชีที่จะบันทึกเมื่อมีการจ่ายเงินยืม (Debit)",
    )

    advance_cash_limit = fields.Float(
        string="Advance Cash Limit", help="วงเงินยืมสูงสุดต่อพนักงาน"
    )
