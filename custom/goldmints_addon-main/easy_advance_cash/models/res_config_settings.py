from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    advance_cash_journal_id = fields.Many2one(
        "account.journal",
        string="Default Advance Cash Journal",
        domain=[("type", "in", ["general", "cash"])],
    )
    advance_cash_reimbursement_journal_id = fields.Many2one(
        "account.journal",
        string="Reimbursement Journal",
        domain=[("type", "=", "purchase")],
        help="สมุดรายวันสำหรับสร้างใบแจ้งหนี้เพื่อคืนเงินส่วนเกินให้พนักงาน",
    )
    advance_cash_reimbursement_account_id = fields.Many2one(
        "account.account",
        string="Reimbursement Account",
        domain=[("deprecated", "=", False)],
        help="บัญชีที่จะบันทึก Debit เมื่อคืนเงินส่วนเกิน (ถ้าไม่ระบุ จะไปตัดบัญชีเงินยืม)",
    )
    advance_cash_return_account_id = fields.Many2one(
        "account.account",
        string="Return Account",
        domain=[("deprecated", "=", False)],
        help="บัญชีที่จะบันทึก Credit เมื่อคืนเงินไม่ครบ (ลูกหนี้/เงินทดรอง)",
    )
    advance_cash_analytic_distribution = fields.Json(
        string="Default Advance Cash Analytic Distribution"
    )

    # Use existing analytic_precision or add it if not present via other modules
    # In easy_petty_cash we added it, so it should be available if both are installed
    # But for safety in this module:
    analytic_precision = fields.Integer(
        store=False,
        default=lambda self: self.env["decimal.precision"].precision_get(
            "Percentage Analytic"
        ),
    )


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    advance_cash_journal_id = fields.Many2one(
        related="company_id.advance_cash_journal_id",
        string="Default Advance Cash Journal",
        readonly=False,
    )
    advance_cash_reimbursement_journal_id = fields.Many2one(
        related="company_id.advance_cash_reimbursement_journal_id",
        string="Reimbursement Journal",
        readonly=False,
    )
    advance_cash_reimbursement_account_id = fields.Many2one(
        related="company_id.advance_cash_reimbursement_account_id",
        string="Reimbursement Account",
        readonly=False,
    )
    advance_cash_return_account_id = fields.Many2one(
        related="company_id.advance_cash_return_account_id",
        string="Return Account",
        readonly=False,
    )
    advance_cash_analytic_distribution = fields.Json(
        related="company_id.advance_cash_analytic_distribution",
        string="Default Advance Cash Analytic Distribution",
        readonly=False,
    )

    analytic_precision = fields.Integer(
        related="company_id.analytic_precision",
        readonly=False,
    )
