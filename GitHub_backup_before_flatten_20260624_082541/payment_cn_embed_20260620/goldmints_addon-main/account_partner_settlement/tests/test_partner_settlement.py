from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import Form
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestPartnerSettlement(TransactionCase):
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
        cls.payable_account = cls.env["account.account"].search(
            [
                ("account_type", "=", "liability_payable"),
                ("company_ids", "in", cls.company.id),
            ],
            limit=1,
        )
        cls.revenue_account = cls.env["account.account"].search(
            [
                ("account_type", "=", "income"),
                ("company_ids", "in", cls.company.id),
            ],
            limit=1,
        )
        cls.expense_account = cls.env["account.account"].search(
            [
                ("account_type", "=", "expense"),
                ("company_ids", "in", cls.company.id),
            ],
            limit=1,
        )
        cls.sale_journal = cls.env["account.journal"].search(
            [("type", "=", "sale"), ("company_id", "=", cls.company.id)],
            limit=1,
        )
        cls.purchase_journal = cls.env["account.journal"].search(
            [("type", "=", "purchase"), ("company_id", "=", cls.company.id)],
            limit=1,
        )
        cls.misc_journal = cls.env["account.journal"].search(
            [("type", "=", "general"), ("company_id", "=", cls.company.id)],
            limit=1,
        )
        cls.bank_journal = cls.env["account.journal"].search(
            [("type", "=", "bank"), ("company_id", "=", cls.company.id)],
            limit=1,
        )
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Settlement Test Partner",
                "approval_state": "approved",
                "is_customer": True,
                "is_supplier": True,
                "customer_rank": 1,
                "supplier_rank": 1,
                "property_account_receivable_id": cls.receivable_account.id,
                "property_account_payable_id": cls.payable_account.id,
                "company_id": False,
            }
        )
        cls.outstanding_payment_account = cls._get_or_create_account(
            "X221001",
            "Settlement Outstanding Payments",
            "liability_current",
        )
        cls.outstanding_receipt_account = cls._get_or_create_account(
            "X122001",
            "Settlement Outstanding Receipts",
            "asset_current",
        )
        bank_journals = cls.env["account.journal"].sudo().search(
            [("type", "=", "bank"), ("company_id", "=", cls.company.id)]
        )
        bank_journals.outbound_payment_method_line_ids.sudo().write(
            {"payment_account_id": cls.outstanding_payment_account.id}
        )
        bank_journals.inbound_payment_method_line_ids.sudo().write(
            {"payment_account_id": cls.outstanding_receipt_account.id}
        )
        cls.wht_account = cls.env["account.account"].create(
            {
                "code": "X152001",
                "name": "Settlement WHT Account",
                "account_type": "asset_current",
                "wht_account": True,
            }
        )
        cls.wht_3 = cls.env["account.withholding.tax"].create(
            {
                "name": "Settlement WHT 3%",
                "account_id": cls.wht_account.id,
                "amount": 3.0,
                "income_tax_form": "pnd53",
                "wht_cert_income_type": "5",
            }
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

    def _create_customer_invoice(self, amount, wht_tax_id=False):
        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "invoice_date": fields.Date.today(),
                "journal_id": self.sale_journal.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "Settlement Sale",
                            "quantity": 1.0,
                            "price_unit": amount,
                            "account_id": self.revenue_account.id,
                            "tax_ids": False,
                        }
                    )
                ],
            }
        )
        if wht_tax_id:
            move.invoice_line_ids.write({"wht_tax_id": wht_tax_id.id})
        move.action_post()
        return move

    def _create_vendor_bill(self, amount, wht_tax_id=False, debit_origin_id=False):
        move = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.partner.id,
                "invoice_date": fields.Date.today(),
                "journal_id": self.purchase_journal.id,
                "debit_origin_id": debit_origin_id and debit_origin_id.id or False,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "Settlement Purchase",
                            "quantity": 1.0,
                            "price_unit": amount,
                            "account_id": self.expense_account.id,
                            "tax_ids": False,
                        }
                    )
                ],
            }
        )
        if wht_tax_id:
            move.invoice_line_ids.write({"wht_tax_id": wht_tax_id.id})
        move.action_post()
        return move

    def _create_vendor_refund(self, amount):
        move = self.env["account.move"].create(
            {
                "move_type": "in_refund",
                "partner_id": self.partner.id,
                "invoice_date": fields.Date.today(),
                "journal_id": self.purchase_journal.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "Settlement Vendor Credit Note",
                            "quantity": 1.0,
                            "price_unit": amount,
                            "account_id": self.expense_account.id,
                            "tax_ids": False,
                        }
                    )
                ],
            }
        )
        move.action_post()
        return move

    def _create_customer_refund(self, amount):
        move = self.env["account.move"].create(
            {
                "move_type": "out_refund",
                "partner_id": self.partner.id,
                "invoice_date": fields.Date.today(),
                "journal_id": self.sale_journal.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "Settlement Customer Credit Note",
                            "quantity": 1.0,
                            "price_unit": amount,
                            "account_id": self.revenue_account.id,
                            "tax_ids": False,
                        }
                    )
                ],
            }
        )
        move.action_post()
        return move

    def _create_settlement_wizard(self, move):
        action = move.action_register_payment()
        wizard_form = Form.from_action(self.env, action)
        wizard_form.journal_id = self.bank_journal
        return wizard_form.save()

    def _create_payment_wizard_from_moves(self, moves):
        action = moves.action_register_payment()
        wizard_form = Form.from_action(self.env, action)
        wizard_form.journal_id = self.bank_journal
        return wizard_form.save()

    def _create_invoice_user(self):
        return self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "Settlement Invoice User",
                "login": "settlement.invoice.user",
                "email": "settlement.invoice.user@example.com",
                "company_id": self.company.id,
                "company_ids": [Command.set([self.company.id])],
                "groups_id": [
                    Command.set(
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref("account.group_account_invoice").id,
                        ]
                    )
                ],
            }
        )

    def test_partner_settlement_creates_traceable_entry(self):
        invoice = self._create_customer_invoice(100.0)
        bill = self._create_vendor_bill(60.0)

        settlement = self.env["account.partner.settlement"].create(
            {
                "partner_id": self.partner.id,
                "journal_id": self.misc_journal.id,
                "date": fields.Date.today(),
            }
        )
        settlement.action_load_open_documents()
        settlement.action_recalculate()
        settlement.action_post_settlement()

        self.assertEqual(settlement.state, "done")
        self.assertTrue(settlement.settlement_move_id)
        self.assertEqual(settlement.settlement_move_id.state, "posted")
        self.assertAlmostEqual(bill.amount_residual, 0.0)
        self.assertAlmostEqual(invoice.amount_residual, 40.0)
        self.assertIn(invoice.name, settlement.settlement_move_id.ref)
        self.assertIn(bill.name, settlement.settlement_move_id.ref)
        self.assertIn(invoice.name, " | ".join(settlement.settlement_move_id.line_ids.mapped("name")))
        self.assertIn(bill.name, " | ".join(settlement.settlement_move_id.line_ids.mapped("name")))

    def test_partner_settlement_blocks_without_both_sides(self):
        self._create_customer_invoice(50.0)
        settlement = self.env["account.partner.settlement"].create(
            {
                "partner_id": self.partner.id,
                "journal_id": self.misc_journal.id,
                "date": fields.Date.today(),
            }
        )
        settlement.action_load_open_documents()
        settlement.line_ids.filtered(lambda line: line.document_kind == "vendor_bill").write({"is_selected": False})
        settlement.action_recalculate()

        with self.assertRaises(UserError):
            settlement.action_post_settlement()

    def test_payment_register_cross_settlement_with_vendor_docs(self):
        invoice = self._create_customer_invoice(100.0)
        bill = self._create_vendor_bill(60.0)
        vendor_debit_note = self._create_vendor_bill(5.0, debit_origin_id=bill)
        vendor_refund = self._create_vendor_refund(10.0)

        wizard = self._create_settlement_wizard(invoice)

        self.assertTrue(wizard.cross_settlement_line_ids)
        self.assertTrue(wizard.journal_id)
        self.assertEqual(
            set(wizard.cross_settlement_line_ids.mapped("move_id").ids),
            {bill.id, vendor_debit_note.id, vendor_refund.id},
        )
        label_map = {
            line.move_id.id: line.document_label
            for line in wizard.cross_settlement_line_ids
        }
        self.assertEqual(label_map[bill.id], "Bill")
        self.assertEqual(label_map[vendor_debit_note.id], "DN")
        self.assertEqual(label_map[vendor_refund.id], "CN")

        wizard.cross_settlement_line_ids.filtered(
            lambda line: line.move_id in (bill, vendor_debit_note, vendor_refund)
        ).write({"is_selected": True})
        wizard._onchange_cross_settlement_line_ids()

        self.assertAlmostEqual(wizard.cross_settlement_amount, 55.0)
        self.assertAlmostEqual(wizard.amount, 45.0)

        action = wizard.action_create_payments()
        self.assertEqual(action["res_model"], "account.payment")

        payment = self.env["account.payment"].browse(action["res_id"])
        self.assertIn(payment.state, ("paid", "in_process"))
        self.assertEqual(payment.move_id.state, "posted")
        self.assertAlmostEqual(payment.amount, 45.0)

        settlement_move = self.env["account.move"].search(
            [
                ("ref", "like", invoice.name),
                ("ref", "like", bill.name),
                ("ref", "like", vendor_debit_note.name),
                ("ref", "like", vendor_refund.name),
            ],
            order="id desc",
            limit=1,
        )
        self.assertTrue(settlement_move)
        self.assertEqual(settlement_move.state, "posted")
        self.assertEqual(settlement_move.journal_id, payment.journal_id)
        self.assertAlmostEqual(invoice.amount_residual, 0.0)
        self.assertAlmostEqual(bill.amount_residual, 0.0)
        self.assertAlmostEqual(vendor_debit_note.amount_residual, 0.0)
        self.assertAlmostEqual(vendor_refund.amount_residual, 0.0)
        self.assertIn(invoice.name, settlement_move.ref)
        self.assertIn(bill.name, settlement_move.ref)
        self.assertIn(vendor_debit_note.name, settlement_move.ref)
        self.assertIn(vendor_refund.name, settlement_move.ref)

    def test_payment_register_customer_credit_note_is_embedded_in_payment_move(self):
        invoice = self._create_customer_invoice(100.0)
        credit_note = self._create_customer_refund(25.0)

        wizard = self._create_payment_wizard_from_moves(invoice | credit_note)
        self.assertAlmostEqual(wizard.amount, 75.0)
        wizard._compute_payment_difference()
        wizard._compute_show_payment_difference()
        self.assertAlmostEqual(wizard.payment_difference, 0.0)
        self.assertFalse(wizard.show_payment_difference)

        action = wizard.action_create_payments()
        self.assertEqual(action["res_model"], "account.payment")
        payment = self.env["account.payment"].browse(action["res_id"])

        receivable_lines = payment.move_id.line_ids.filtered(
            lambda line: line.account_id == self.receivable_account
        )
        self.assertAlmostEqual(sum(receivable_lines.mapped("debit")), 25.0)
        self.assertAlmostEqual(sum(receivable_lines.mapped("credit")), 100.0)
        self.assertIn(credit_note.name, " | ".join(receivable_lines.mapped("name")))
        self.assertAlmostEqual(invoice.amount_residual, 0.0)
        self.assertAlmostEqual(credit_note.amount_residual, 0.0)

    def test_payment_register_vendor_credit_note_is_embedded_in_payment_move(self):
        bill = self._create_vendor_bill(100.0)
        credit_note = self._create_vendor_refund(25.0)

        wizard = self._create_payment_wizard_from_moves(bill | credit_note)
        self.assertAlmostEqual(wizard.amount, 75.0)
        wizard._compute_payment_difference()
        wizard._compute_show_payment_difference()
        self.assertAlmostEqual(wizard.payment_difference, 0.0)
        self.assertFalse(wizard.show_payment_difference)

        action = wizard.action_create_payments()
        self.assertEqual(action["res_model"], "account.payment")
        payment = self.env["account.payment"].browse(action["res_id"])

        payable_lines = payment.move_id.line_ids.filtered(
            lambda line: line.account_id == self.payable_account
        )
        self.assertAlmostEqual(sum(payable_lines.mapped("debit")), 100.0)
        self.assertAlmostEqual(sum(payable_lines.mapped("credit")), 25.0)
        self.assertIn(credit_note.name, " | ".join(payable_lines.mapped("name")))
        self.assertAlmostEqual(bill.amount_residual, 0.0)
        self.assertAlmostEqual(credit_note.amount_residual, 0.0)

    def test_payment_register_cross_settlement_syncs_allocation_to_net_amount(self):
        invoice = self._create_customer_invoice(100.0)
        bill = self._create_vendor_bill(60.0)

        wizard = self._create_settlement_wizard(invoice)
        settlement_line = wizard.cross_settlement_line_ids.filtered(lambda line: line.move_id == bill)
        settlement_line.is_selected = True
        wizard._onchange_cross_settlement_line_ids()

        self.assertAlmostEqual(wizard.cross_settlement_amount, 60.0)
        self.assertAlmostEqual(wizard.amount, 40.0)
        self.assertAlmostEqual(sum(wizard.allocation_line_ids.mapped("amount_to_pay")), 40.0)
        self.assertAlmostEqual(sum(wizard.allocation_line_ids.mapped("amount_residual")), 60.0)

    def test_payment_register_cross_settlement_manual_amount_updates_allocation(self):
        invoice = self._create_customer_invoice(100.0)
        bill = self._create_vendor_bill(60.0)

        wizard = self._create_settlement_wizard(invoice)
        settlement_line = wizard.cross_settlement_line_ids.filtered(lambda line: line.move_id == bill)
        settlement_line.is_selected = True
        wizard._onchange_cross_settlement_line_ids()

        wizard.amount = 25.0
        wizard._onchange_amount()

        self.assertAlmostEqual(wizard.amount, 25.0)
        self.assertAlmostEqual(sum(wizard.allocation_line_ids.mapped("amount_to_pay")), 25.0)
        self.assertAlmostEqual(sum(wizard.allocation_line_ids.mapped("amount_residual")), 75.0)

    def test_payment_register_cross_settlement_keeps_net_amount_after_context_change(self):
        invoice = self._create_customer_invoice(100.0)
        bill = self._create_vendor_bill(60.0)

        wizard = self._create_settlement_wizard(invoice)
        settlement_line = wizard.cross_settlement_line_ids.filtered(lambda line: line.move_id == bill)
        settlement_line.is_selected = True
        wizard._onchange_cross_settlement_line_ids()
        wizard.amount = 25.0
        wizard._onchange_amount()

        alt_journal = self.bank_journal.copy(
            {
                "name": "Settlement Alt Bank",
                "code": "STAB2",
            }
        )
        wizard.journal_id = alt_journal
        wizard.payment_date = fields.Date.add(fields.Date.today(), days=1)
        wizard._onchange_allocation_context_fields()

        self.assertAlmostEqual(wizard.amount, 25.0)
        self.assertAlmostEqual(sum(wizard.allocation_line_ids.mapped("amount_to_pay")), 25.0)
        self.assertAlmostEqual(sum(wizard.allocation_line_ids.mapped("amount_residual")), 75.0)

    def test_payment_register_default_get_preloads_cross_settlement(self):
        invoice = self._create_customer_invoice(100.0)
        bill = self._create_vendor_bill(60.0)

        action = invoice.action_register_payment()
        model = self.env["account.payment.register"].with_context(**action["context"])
        defaults = model.default_get(
            [
                "partner_id",
                "company_id",
                "partner_type",
                "currency_id",
                "cross_settlement_line_ids",
            ]
        )

        self.assertEqual(defaults["partner_id"], self.partner.id)
        self.assertEqual(defaults["company_id"], self.company.id)
        self.assertEqual(defaults["partner_type"], "customer")
        self.assertEqual(defaults["currency_id"], self.company.currency_id.id)
        self.assertTrue(defaults["cross_settlement_line_ids"])

        wizard = model.new(defaults)
        self.assertTrue(wizard.show_cross_settlement)
        self.assertEqual(set(wizard.cross_settlement_line_ids.mapped("move_id").ids), {bill.id})

    def test_payment_register_new_record_onchange_handles_unsaved_cross_lines(self):
        invoice = self._create_customer_invoice(100.0)
        bill = self._create_vendor_bill(60.0)

        action = invoice.action_register_payment()
        model = self.env["account.payment.register"].with_context(**action["context"])
        defaults = model.default_get(
            [
                "partner_id",
                "company_id",
                "partner_type",
                "currency_id",
                "cross_settlement_line_ids",
            ]
        )
        wizard = model.new(defaults)
        line = wizard.cross_settlement_line_ids.filtered(lambda record: record.move_id == bill)[:1]
        self.assertTrue(line)

        line.is_selected = True
        wizard._onchange_cross_settlement_line_ids()

        self.assertAlmostEqual(wizard.cross_settlement_amount, 60.0)

    def test_payment_register_refresh_cross_lines_replaces_instead_of_duplicate(self):
        invoice = self._create_customer_invoice(100.0)
        bill = self._create_vendor_bill(60.0)

        wizard = self._create_settlement_wizard(invoice)
        self.assertEqual(set(wizard.cross_settlement_line_ids.mapped("move_id").ids), {bill.id})

        wizard._refresh_cross_settlement_lines()
        wizard._refresh_cross_settlement_lines()

        self.assertEqual(len(wizard.cross_settlement_line_ids), 1)
        self.assertEqual(set(wizard.cross_settlement_line_ids.mapped("move_id").ids), {bill.id})

    def test_payment_register_create_accepts_stale_settlement_journal_payload(self):
        invoice = self._create_customer_invoice(100.0)
        ctx = {
            "active_ids": [invoice.id],
            "active_id": invoice.id,
            "active_model": "account.move",
        }
        wizard = self.env["account.payment.register"].with_context(**ctx).create(
            {
                "journal_id": self.bank_journal.id,
                "settlement_journal_id": self.bank_journal.id,
            }
        )
        self.assertEqual(wizard.journal_id, self.bank_journal)

    def test_payment_register_create_deduplicates_cross_settlement_payload(self):
        invoice = self._create_customer_invoice(100.0)
        bill = self._create_vendor_bill(60.0)
        ctx = {
            "active_ids": [invoice.id],
            "active_id": invoice.id,
            "active_model": "account.move",
        }
        wizard = self.env["account.payment.register"].with_context(**ctx).create(
            {
                "journal_id": self.bank_journal.id,
                "cross_settlement_line_ids": [
                    Command.create(
                        {
                            "move_id": bill.id,
                            "currency_id": self.company.currency_id.id,
                            "account_id": self.payable_account.id,
                            "residual_signed_amount": 60.0,
                            "amount_to_settle": 60.0,
                            "is_selected": True,
                        }
                    ),
                    Command.create(
                        {
                            "move_id": bill.id,
                            "currency_id": self.company.currency_id.id,
                            "account_id": self.payable_account.id,
                            "residual_signed_amount": 60.0,
                            "amount_to_settle": 0.0,
                            "is_selected": False,
                        }
                    ),
                ],
            }
        )
        self.assertEqual(len(wizard.cross_settlement_line_ids), 1)
        self.assertEqual(wizard.cross_settlement_line_ids.move_id, bill)
        self.assertTrue(wizard.cross_settlement_line_ids.is_selected)
        self.assertAlmostEqual(wizard.cross_settlement_line_ids.amount_to_settle, 60.0)

    def test_payment_register_cross_settlement_supports_multi_deduction(self):
        invoice = self._create_customer_invoice(100.0)
        bill = self._create_vendor_bill(60.0)
        vendor_refund = self._create_vendor_refund(10.0)

        wizard = self._create_settlement_wizard(invoice)
        wizard.cross_settlement_line_ids.filtered(
            lambda line: line.move_id in (bill, vendor_refund)
        ).write({"is_selected": True})
        wizard._onchange_cross_settlement_line_ids()

        if "custom_user_amount" in wizard._fields:
            wizard.custom_user_amount = True
        if "custom_user_currency_id" in wizard._fields:
            wizard.custom_user_currency_id = wizard.currency_id
        wizard.amount = 45.0
        wizard.deduction_ids = [
            Command.create(
                {
                    "account_id": self.expense_account.id,
                    "name": "Settlement Charge",
                    "amount": 5.0,
                }
            )
        ]
        wizard.payment_difference_handling = "reconcile_multi_deduct"
        wizard._compute_payment_difference()

        self.assertAlmostEqual(wizard.cross_settlement_amount, 50.0)
        self.assertAlmostEqual(wizard.payment_difference, 5.0)

        action = wizard.action_create_payments()
        payment = self.env["account.payment"].browse(action["res_id"])
        self.assertIn(payment.state, ("paid", "in_process"))
        self.assertAlmostEqual(payment.amount, 45.0)
        settlement_move = self.env["account.move"].search(
            [("ref", "like", invoice.name), ("ref", "like", bill.name), ("ref", "like", vendor_refund.name)],
            order="id desc",
            limit=1,
        )
        self.assertEqual(settlement_move.journal_id, payment.journal_id)
        self.assertAlmostEqual(invoice.amount_residual, 0.0)
        self.assertAlmostEqual(bill.amount_residual, 0.0)
        self.assertAlmostEqual(vendor_refund.amount_residual, 0.0)

    def test_payment_register_cross_settlement_clears_stale_auto_difference_lines(self):
        invoice = self._create_customer_invoice(100.0)
        bill = self._create_vendor_bill(60.0)

        self.company.auto_diff_account_id = self.expense_account
        self.company.auto_diff_label = "Difference"

        wizard = self._create_settlement_wizard(invoice)
        wizard.cross_settlement_line_ids.filtered(lambda line: line.move_id == bill).write({"is_selected": True})
        wizard._onchange_cross_settlement_line_ids()

        wizard.payment_difference_handling = "reconcile_multi_deduct"
        wizard.deduction_ids = [
            Command.create(
                {
                    "account_id": self.expense_account.id,
                    "name": "Difference",
                    "amount": -60.0,
                }
            )
        ]

        wizard._cleanup_cross_settlement_auto_deductions()
        wizard._compute_payment_difference()

        self.assertFalse(wizard.deduction_ids)
        self.assertEqual(wizard.payment_difference_handling, "open")
        self.assertAlmostEqual(wizard.payment_difference, 0.0)

    def test_payment_register_cross_settlement_onchange_does_not_leave_auto_difference_deduction(self):
        invoice = self._create_customer_invoice(100.0)
        bill = self._create_vendor_bill(60.0)

        self.company.auto_diff_account_id = self.expense_account
        self.company.auto_diff_label = "Difference"

        wizard = self._create_settlement_wizard(invoice)
        wizard.cross_settlement_line_ids.filtered(lambda line: line.move_id == bill).write({"is_selected": True})
        wizard._onchange_cross_settlement_line_ids()
        wizard._compute_payment_difference()
        wizard._onchange_payment_difference_auto_deduction()

        self.assertFalse(wizard.deduction_ids)
        self.assertEqual(wizard.payment_difference_handling, "open")
        self.assertAlmostEqual(wizard.cross_settlement_amount, 60.0)
        self.assertAlmostEqual(wizard.amount, 40.0)
        self.assertAlmostEqual(wizard.payment_difference, 0.0)

    def test_payment_register_cross_settlement_supports_wht(self):
        vendor_bill = self._create_vendor_bill(100.0, wht_tax_id=self.wht_3)
        customer_invoice = self._create_customer_invoice(40.0)
        customer_refund = self._create_customer_refund(10.0)

        wizard = Form.from_action(self.env, vendor_bill.action_register_payment()).save()

        label_map = {
            line.move_id.id: line.document_label
            for line in wizard.cross_settlement_line_ids
        }
        self.assertEqual(label_map[customer_invoice.id], "Invoice")
        self.assertEqual(label_map[customer_refund.id], "CN")

        wizard.cross_settlement_line_ids.filtered(
            lambda line: line.move_id in (customer_invoice, customer_refund)
        ).write({"is_selected": True})
        wizard._onchange_cross_settlement_line_ids()
        wizard._compute_payment_difference()

        self.assertEqual(wizard.payment_difference_handling, "reconcile")
        self.assertAlmostEqual(wizard.cross_settlement_amount, 30.0)
        self.assertAlmostEqual(wizard.amount, 67.0)
        self.assertAlmostEqual(sum(wizard.allocation_line_ids.mapped("amount_to_pay")), 67.0)
        self.assertAlmostEqual(wizard.payment_difference, 0.0)

        action = wizard.action_create_payments()
        payment = self.env["account.payment"].browse(action["res_id"])
        self.assertIn(payment.state, ("paid", "in_process"))
        self.assertAlmostEqual(payment.amount, 67.0)
        settlement_move = self.env["account.move"].search(
            [("ref", "like", vendor_bill.name), ("ref", "like", customer_invoice.name), ("ref", "like", customer_refund.name)],
            order="id desc",
            limit=1,
        )
        self.assertEqual(settlement_move.journal_id, payment.journal_id)
        self.assertAlmostEqual(vendor_bill.amount_residual, 0.0)
        self.assertAlmostEqual(customer_invoice.amount_residual, 0.0)
        self.assertAlmostEqual(customer_refund.amount_residual, 0.0)

    def test_payment_register_ar_to_ap_settlement_creates_wht_cert_from_settlement(self):
        customer_invoice = self._create_customer_invoice(100.0)
        vendor_bill = self._create_vendor_bill(60.0, wht_tax_id=self.wht_3)

        wizard = self._create_settlement_wizard(customer_invoice)
        wizard.cross_settlement_line_ids.filtered(lambda line: line.move_id == vendor_bill).write(
            {"is_selected": True}
        )
        wizard._onchange_cross_settlement_line_ids()
        wizard._compute_payment_difference()

        self.assertAlmostEqual(wizard.cross_settlement_amount, 60.0)
        self.assertAlmostEqual(wizard.amount, 41.8)
        self.assertAlmostEqual(wizard.payment_difference, 0.0)

        action = wizard.action_create_payments()
        payment = self.env["account.payment"].browse(action["res_id"])
        self.assertIn(payment.state, ("paid", "in_process"))
        self.assertAlmostEqual(payment.amount, 41.8)

        settlement_move = self.env["account.move"].search(
            [("ref", "like", customer_invoice.name), ("ref", "like", vendor_bill.name)],
            order="id desc",
            limit=1,
        )
        self.assertTrue(settlement_move)
        self.assertEqual(settlement_move.state, "posted")
        self.assertAlmostEqual(customer_invoice.amount_residual, 0.0)
        self.assertAlmostEqual(vendor_bill.amount_residual, 0.0)
        self.assertAlmostEqual(sum(settlement_move.wht_move_ids.mapped("amount_income")), 60.0)
        self.assertAlmostEqual(sum(settlement_move.wht_move_ids.mapped("amount_wht")), 1.8)
        self.assertEqual(len(settlement_move.wht_cert_ids), 1)
        self.assertAlmostEqual(sum(settlement_move.wht_cert_ids.wht_line.mapped("base")), 60.0)
        self.assertAlmostEqual(sum(settlement_move.wht_cert_ids.wht_line.mapped("amount")), 1.8)

    def test_payment_register_ap_to_ar_full_settlement_creates_wht_cert_without_cash_payment(self):
        vendor_bill = self._create_vendor_bill(100.0, wht_tax_id=self.wht_3)
        customer_invoice = self._create_customer_invoice(97.0)

        wizard = Form.from_action(self.env, vendor_bill.action_register_payment()).save()
        wizard.cross_settlement_line_ids.filtered(lambda line: line.move_id == customer_invoice).write(
            {"is_selected": True}
        )
        wizard._onchange_cross_settlement_line_ids()
        wizard._compute_payment_difference()

        self.assertAlmostEqual(wizard.cross_settlement_amount, 97.0)
        self.assertAlmostEqual(wizard.amount, 0.0)
        self.assertAlmostEqual(wizard.payment_difference, 0.0)

        action = wizard.action_create_payments()
        self.assertEqual(action["res_model"], "account.move")

        settlement_move = self.env["account.move"].browse(action["res_id"])
        self.assertEqual(settlement_move.state, "posted")
        self.assertFalse(settlement_move.origin_payment_id)
        self.assertAlmostEqual(vendor_bill.amount_residual, 0.0)
        self.assertAlmostEqual(customer_invoice.amount_residual, 0.0)
        self.assertAlmostEqual(sum(settlement_move.wht_move_ids.mapped("amount_income")), 100.0)
        self.assertAlmostEqual(sum(settlement_move.wht_move_ids.mapped("amount_wht")), 3.0)
        self.assertEqual(len(settlement_move.wht_cert_ids), 1)
        self.assertAlmostEqual(sum(settlement_move.wht_cert_ids.wht_line.mapped("base")), 100.0)
        self.assertAlmostEqual(sum(settlement_move.wht_cert_ids.wht_line.mapped("amount")), 3.0)

    def test_payment_register_cross_settlement_preserves_manual_amount_for_deduction_with_wht(self):
        vendor_bill = self._create_vendor_bill(100.0, wht_tax_id=self.wht_3)
        customer_invoice = self._create_customer_invoice(40.0)
        customer_refund = self._create_customer_refund(10.0)

        wizard = Form.from_action(self.env, vendor_bill.action_register_payment()).save()
        wizard.cross_settlement_line_ids.filtered(
            lambda line: line.move_id in (customer_invoice, customer_refund)
        ).write({"is_selected": True})
        wizard._onchange_cross_settlement_line_ids()

        wizard.amount = 60.0
        wizard._onchange_amount()
        wizard.payment_difference_handling = "reconcile_multi_deduct"
        wizard.deduction_ids = [
            Command.create(
                {
                    "account_id": self.expense_account.id,
                    "name": "Settlement Charge",
                    "amount": 7.0,
                }
            )
        ]
        wizard._compute_amount()
        wizard._compute_payment_difference()
        wizard._onchange_allocation_context_fields()

        self.assertAlmostEqual(wizard.amount, 60.0)
        self.assertAlmostEqual(sum(wizard.allocation_line_ids.mapped("amount_to_pay")), 60.0)
        self.assertAlmostEqual(wizard.payment_difference, 7.0)
        self.assertTrue(wizard.custom_user_amount)

        action = wizard.action_create_payments()
        payment = self.env["account.payment"].browse(action["res_id"])
        self.assertAlmostEqual(payment.amount, 60.0)
        manual_deduction_lines = payment.move_id.line_ids.filtered(
            lambda line: line.account_id == self.expense_account and line.name == "Settlement Charge"
        )
        self.assertAlmostEqual(sum(abs(line.balance) for line in manual_deduction_lines), 7.0)
        settlement_move = self.env["account.move"].search(
            [("ref", "like", vendor_bill.name), ("ref", "like", customer_invoice.name), ("ref", "like", customer_refund.name)],
            order="id desc",
            limit=1,
        )
        self.assertAlmostEqual(vendor_bill.amount_residual, 0.0)
        self.assertAlmostEqual(customer_invoice.amount_residual, 0.0)
        self.assertAlmostEqual(customer_refund.amount_residual, 0.0)
        self.assertAlmostEqual(sum(settlement_move.wht_move_ids.mapped("amount_wht")), 3.0)

    def test_payment_register_cross_settlement_form_keeps_amount_editable(self):
        invoice = self._create_customer_invoice(100.0)
        self._create_vendor_bill(60.0)

        wizard_form = Form.from_action(self.env, invoice.action_register_payment())
        self.assertFalse(wizard_form._get_modifier("amount", "readonly"))
        with wizard_form.cross_settlement_line_ids.edit(0) as settlement_line:
            settlement_line.is_selected = True
        self.assertFalse(wizard_form._get_modifier("amount", "readonly"))
        wizard_form.amount = 25.0
        self.assertAlmostEqual(wizard_form.amount, 25.0)

    def test_payment_register_normal_customer_form_keeps_amount_editable(self):
        customer = self.env["res.partner"].create(
            {
                "name": "Settlement Normal Customer",
                "approval_state": "approved",
                "is_customer": True,
                "is_supplier": False,
                "customer_rank": 1,
                "supplier_rank": 0,
                "property_account_receivable_id": self.receivable_account.id,
                "property_account_payable_id": self.payable_account.id,
                "company_id": False,
            }
        )
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": customer.id,
                "invoice_date": fields.Date.today(),
                "journal_id": self.sale_journal.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "Normal Sale",
                            "quantity": 1.0,
                            "price_unit": 100.0,
                            "account_id": self.revenue_account.id,
                            "tax_ids": False,
                        }
                    )
                ],
            }
        )
        invoice.action_post()

        wizard_form = Form.from_action(self.env, invoice.action_register_payment())

        self.assertFalse(wizard_form._get_modifier("amount", "readonly"))
        wizard_form.amount = 25.0
        self.assertAlmostEqual(wizard_form.amount, 25.0)

    def test_payment_register_cross_settlement_form_multi_deduction_uses_net_difference(self):
        invoice = self._create_customer_invoice(100.0)
        self._create_vendor_bill(60.0)

        wizard_form = Form.from_action(self.env, invoice.action_register_payment())
        with wizard_form.cross_settlement_line_ids.edit(0) as settlement_line:
            settlement_line.is_selected = True
        wizard_form.amount = 33.0

        wizard = wizard_form.save()
        wizard.payment_difference_handling = "reconcile_multi_deduct"
        wizard.deduction_ids = [
            Command.create(
                {
                    "account_id": self.expense_account.id,
                    "name": "Settlement Charge",
                    "amount": 7.0,
                }
            )
        ]
        wizard._compute_payment_difference()

        self.assertAlmostEqual(wizard.cross_settlement_amount, 60.0)
        self.assertAlmostEqual(wizard.payment_difference, 7.0)
        self.assertAlmostEqual(wizard._get_cross_expected_deduction_amount(), 7.0)
        wizard._check_deduction_amount()

    def test_payment_register_cross_settlement_customer_wht_manual_deduction_uses_net_difference(self):
        invoice = self._create_customer_invoice(100.0, wht_tax_id=self.wht_3)
        bill = self._create_vendor_bill(40.0)

        wizard = self._create_settlement_wizard(invoice)
        wizard.cross_settlement_line_ids.filtered(lambda line: line.move_id == bill).write({"is_selected": True})
        wizard._onchange_cross_settlement_line_ids()
        wizard.amount = 53.0
        wizard._onchange_amount()
        wizard.payment_difference_handling = "reconcile_multi_deduct"
        wizard.deduction_ids = [
            Command.create(
                {
                    "account_id": self.expense_account.id,
                    "name": "Settlement Charge",
                    "amount": 7.0,
                }
            )
        ]
        wizard._compute_payment_difference()

        self.assertAlmostEqual(wizard.cross_settlement_amount, 40.0)
        self.assertAlmostEqual(wizard.amount, 53.0)
        self.assertAlmostEqual(wizard.payment_difference, 7.0)
        self.assertAlmostEqual(wizard._get_cross_expected_deduction_amount(), 7.0)
        wizard._check_deduction_amount()

    def test_payment_register_cross_settlement_requires_customer_and_supplier_partner(self):
        invoice = self._create_customer_invoice(100.0)
        self._create_vendor_bill(60.0)

        self.partner.write(
            {
                "is_supplier": False,
                "supplier_rank": 0,
            }
        )

        wizard = self._create_settlement_wizard(invoice)

        self.assertFalse(wizard.show_cross_settlement)
        self.assertFalse(wizard.cross_settlement_line_ids)

    def test_payment_register_cross_settlement_available_for_invoice_user_group(self):
        invoice_user = self._create_invoice_user()
        invoice = self._create_customer_invoice(100.0)
        bill = self._create_vendor_bill(60.0)

        action = invoice.with_user(invoice_user).action_register_payment()
        wizard = (
            self.env["account.payment.register"]
            .with_user(invoice_user)
            .with_context(**action["context"])
            .create({})
        )

        self.assertTrue(wizard.show_cross_settlement)
        self.assertEqual(set(wizard.cross_settlement_line_ids.mapped("move_id").ids), {bill.id})

    def test_payment_register_cross_settlement_keeps_payment_difference_controls_when_core_edit_is_false(self):
        invoice = self._create_customer_invoice(100.0)
        bill = self._create_vendor_bill(60.0)

        wizard = self._create_settlement_wizard(invoice)
        wizard.cross_settlement_line_ids.filtered(lambda line: line.move_id == bill).write({"is_selected": True})
        wizard._onchange_cross_settlement_line_ids()
        wizard.amount = 25.0
        wizard._onchange_amount()
        wizard.can_edit_wizard = False
        wizard.cross_settlement_amount_editable = True
        wizard._compute_payment_difference()
        wizard._compute_payment_difference_handling()
        wizard._compute_show_payment_difference()

        self.assertAlmostEqual(wizard.payment_difference, 15.0)
        self.assertEqual(wizard.payment_difference_handling, "open")
        self.assertTrue(wizard.show_payment_difference)
