from odoo import Command, fields
from odoo.tests import Form, tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestPaymentDefaultJournal(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.receivable_account = cls.env["account.account"].search(
            [
                ("account_type", "=", "asset_receivable"),
                ("company_ids", "in", cls.company.id),
            ],
            limit=1,
        )
        cls.income_account = cls.env["account.account"].search(
            [
                ("account_type", "=", "income"),
                ("company_ids", "in", cls.company.id),
            ],
            limit=1,
        )
        cls.sale_journal = cls.env["account.journal"].search(
            [("type", "=", "sale"), ("company_id", "=", cls.company.id)],
            limit=1,
        )
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Default Payment Journal Test Partner",
                "approval_state": "approved",
                "is_customer": True,
                "customer_rank": 1,
                "property_account_receivable_id": cls.receivable_account.id,
                "company_id": False,
            }
        )
        cls.outstanding_receipt_account = cls._get_or_create_account(
            "X123910",
            "Default Journal Test Outstanding Receipt",
            "asset_current",
        )
        cls.bad_journal = cls._get_or_create_bank_journal("DPJBAD", "Default Journal Test Bad")
        cls.good_journal = cls._get_or_create_bank_journal("DPJOK", "Default Journal Test Good")
        cls.bad_journal.inbound_payment_method_line_ids.write({"payment_account_id": False})
        cls.good_journal.inbound_payment_method_line_ids[:1].write(
            {"payment_account_id": cls.outstanding_receipt_account.id}
        )

    @classmethod
    def _get_or_create_account(cls, code, name, account_type):
        account = cls.env["account.account"].search(
            [
                ("code", "=", code),
                ("company_ids", "in", cls.company.id),
            ],
            limit=1,
        )
        if account:
            return account
        return cls.env["account.account"].create(
            {
                "code": code,
                "name": name,
                "account_type": account_type,
            }
        )

    @classmethod
    def _get_or_create_bank_journal(cls, code, name):
        journal = cls.env["account.journal"].search(
            [
                ("code", "=", code),
                ("company_id", "=", cls.company.id),
            ],
            limit=1,
        )
        if journal:
            return journal
        return cls.env["account.journal"].create(
            {
                "name": name,
                "code": code,
                "type": "bank",
                "company_id": cls.company.id,
            }
        )

    def _create_invoice(self, amount):
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "invoice_date": fields.Date.today(),
                "journal_id": self.sale_journal.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "Default Journal Test Sale",
                            "quantity": 1.0,
                            "price_unit": amount,
                            "account_id": self.income_account.id,
                        }
                    )
                ],
            }
        )
        invoice.action_post()
        return invoice

    def test_default_ar_journal_falls_back_when_method_has_no_outstanding_account(self):
        self.company.write(
            {
                "pmt_ar_journal_id": self.bad_journal.id,
                "pmt_ar_payment_method_id": self.bad_journal.inbound_payment_method_line_ids[:1].id,
            }
        )
        invoice = self._create_invoice(100.0)
        action = invoice.action_register_payment()
        wizard_form = Form(self.env["account.payment.register"].with_context(action["context"]))
        wizard = wizard_form.save()

        self.assertNotEqual(wizard.journal_id, self.bad_journal)
        self.assertTrue(wizard.payment_method_line_id.payment_account_id)

        payment_action = wizard.action_create_payments()
        payment = self.env["account.payment"].browse(payment_action["res_id"])
        self.assertTrue(payment.move_id)
        self.assertAlmostEqual(invoice.amount_residual, 0.0)
