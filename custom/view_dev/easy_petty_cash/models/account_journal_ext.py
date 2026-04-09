from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    petty_cash_wht_account_id = fields.Many2one(
        "account.account",
        string="Petty Cash Account",
        domain="[('deprecated', '=', False)]",
        help="ระบุบัญชีสำหรับหัก (เช่น 213000) ถ้าไม่ระบุจะใช้ตาม Tax Setting",
    )

    petty_cash_limit = fields.Float(
        string="Petty Cash Limit", help="วงเงินสูงสุดของเงินสดย่อย"
    )
