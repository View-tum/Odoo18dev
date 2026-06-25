from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "easy_advance_cash_bank_draft")
class TestAdvanceBankDraft(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.currency = cls.company.currency_id
        cls.partner = cls.env["res.partner"].create({"name": "Advance Bank Draft Employee"})
        cls.employee = cls.env["hr.employee"].create({
            "name": "Advance Bank Draft Employee",
            "work_contact_id": cls.partner.id,
        })
        cls.advance_account = cls.env["account.account"].create({
            "name": "Advance Bank Draft Test Advance",
            "code": "TADVBD",
            "account_type": "asset_current",
            "company_ids": [(6, 0, cls.company.ids)],
        })
        cls.bank_account = cls.env["account.account"].create({
            "name": "Advance Bank Draft Test Bank",
            "code": "TBKBD",
            "account_type": "asset_cash",
            "company_ids": [(6, 0, cls.company.ids)],
        })
        cls.advance_journal = cls.env["account.journal"].create({
            "name": "Advance Bank Draft Journal",
            "code": "ABDJ",
            "type": "general",
            "advance_account_id": cls.advance_account.id,
            "default_account_id": cls.advance_account.id,
            "company_id": cls.company.id,
        })
        cls.bank_journal = cls.env["account.journal"].create({
            "name": "Advance Bank Draft Bank",
            "code": "ABDB",
            "type": "bank",
            "default_account_id": cls.bank_account.id,
            "company_id": cls.company.id,
        })
        cls.bank_draft_method = cls.env["account.payment.method"].search([
            ("code", "=", "bank_draft"),
            ("payment_type", "=", "inbound"),
        ], limit=1)
        if not cls.bank_draft_method:
            raise AssertionError("Inbound bank draft payment method is not installed")
        cls.bank_draft_method_line = cls.env["account.payment.method.line"].create({
            "name": "Bank Draft Test",
            "payment_method_id": cls.bank_draft_method.id,
            "journal_id": cls.bank_journal.id,
            "payment_account_id": cls.bank_account.id,
            "is_bank_draft_incoming_line": True,
        })

    def test_return_advance_creates_inbound_bank_draft_audit_record(self):
        self.assertIn("instrument_type", self.env["cheque.inbound.outbound"]._fields)
        self.env["advance.cash.log"].create({
            "transaction_type": "payout",
            "employee_id": self.employee.id,
            "description": "Existing advance balance",
            "amount": 5000.0,
            "journal_id": self.advance_journal.id,
            "state": "posted",
        })
        self.employee._compute_advance_balance()
        bank = self.env["res.bank"].create({"name": "Bank Draft Test Bank"})
        advance = self.env["advance.cash.log"].create({
            "transaction_type": "return",
            "employee_id": self.employee.id,
            "description": "Return advance by bank draft",
            "amount": 2500.0,
            "journal_id": self.advance_journal.id,
            "state": "submitted",
            "return_payment_journal_id": self.bank_journal.id,
            "return_payment_method_line_id": self.bank_draft_method_line.id,
            "bank_draft_number": "BD-TEST-001",
            "bank_draft_bank_id": bank.id,
            "bank_draft_branch": "HQ",
            "bank_draft_date": fields.Date.today(),
        })
        advance.action_manager_approve()
        advance.action_approve()
        draft = self.env["cheque.inbound.outbound"].search([
            ("name", "=", "BD-TEST-001"),
            ("instrument_type", "=", "bank_draft"),
            ("cheque_type", "=", "inbound"),
            ("pay_partner_id", "=", self.partner.id),
        ], limit=1)
        self.assertTrue(draft)
        self.assertEqual(draft.amount, advance.amount)
        self.assertFalse(draft.cheque_journal_entry_id)
        self.assertEqual(draft.cheque_bank_id, bank)
        self.assertEqual(draft.cheque_bank_branch, "HQ")
        self.assertEqual(advance.bank_draft_id, draft)
        advance.action_confirm()
        self.assertEqual(draft.cheque_journal_entry_id, advance.move_id)
        self.assertEqual(advance.state, "posted")
