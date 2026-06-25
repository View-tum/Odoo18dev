import inspect
from pathlib import Path

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools.misc import file_path


@tagged("post_install", "-at_install")
class TestMobileMixedPayment(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Test Partner Mobile Mixed"})
        if "approval_state" in cls.partner._fields:
            cls.partner.write({"approval_state": "approved"})
        if "ecom_exempt" in cls.partner._fields:
            cls.partner.write({"ecom_exempt": True})

        cls.so_type = cls.env["sale.sequence.type"].search([], limit=1) or cls.env["sale.sequence.type"].create(
            {
                "name": "Domestic Type Test",
                "market_scope": "domestic",
            }
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Mobile Mixed Payment Product",
                "type": "service",
                "invoice_policy": "order",
                "list_price": 1000.0,
                "taxes_id": [Command.clear()],
            }
        )
        if "approval_state" in cls.product.product_tmpl_id._fields:
            cls.product.product_tmpl_id.write({"approval_state": "approved"})
        cls.warehouse = cls.env["stock.warehouse"].create(
            {
                "name": "Mobile Warehouse Payment Test",
                "code": "MWPT",
                "company_id": cls.env.company.id,
            }
        )
        cls.receipt_account = cls.env["account.account"].search(
            [
                ("company_ids", "in", cls.env.company.id),
                ("account_type", "=", "asset_current"),
            ],
            limit=1,
        )
        cls.rounding_account = cls.env["account.account"].search(
            [
                ("company_ids", "in", cls.env.company.id),
                ("account_type", "=", "expense"),
            ],
            limit=1,
        )
        cls.income_account = cls.env["account.account"].search(
            [
                ("company_ids", "in", cls.env.company.id),
                ("account_type", "=", "income"),
            ],
            limit=1,
        )
        cls.sale_journal = cls.env["account.journal"].search(
            [("type", "=", "sale"), ("company_id", "=", cls.env.company.id)],
            limit=1,
        )
        cls.bank_journal = cls.env["account.journal"].create(
            {
                "name": "Mobile Bank Receipt Test",
                "code": "MBRT",
                "type": "bank",
                "company_id": cls.env.company.id,
            }
        )
        cls.cash_journal = cls.env["account.journal"].create(
            {
                "name": "Mobile Cash Receipt Test",
                "code": "MCRT",
                "type": "cash",
                "company_id": cls.env.company.id,
            }
        )
        cls.cheque_journal = cls.env["account.journal"].create(
            {
                "name": "Mobile Cheque Receipt Test",
                "code": "MQRT",
                "type": "bank",
                "company_id": cls.env.company.id,
                "is_cheque_incoming": True,
            }
        )
        cls.bank_journal.inbound_payment_method_line_ids[:1].payment_account_id = (
            cls.receipt_account
        )
        cls.cash_journal.inbound_payment_method_line_ids[:1].payment_account_id = (
            cls.receipt_account
        )
        cls.cheque_journal.inbound_payment_method_line_ids[:1].payment_account_id = (
            cls.receipt_account
        )
        cls.cheque_method_line = cls.env["account.payment.method.line"].create(
            {
                "name": "Mobile Cheque Incoming Test",
                "journal_id": cls.cheque_journal.id,
                "payment_method_id": cls.env.ref(
                    "cheque_management.account_payment_method_cheque_in"
                ).id,
                "payment_account_id": cls.receipt_account.id,
                "is_cheque_incoming_line": True,
            }
        )
        cls.env.company.write(
            {
                "mobile_bank_transfer_journal_id": cls.bank_journal.id,
                "mobile_cash_journal_id": cls.cash_journal.id,
                "mobile_cheque_journal_id": cls.cheque_journal.id,
                "auto_diff_account_id": cls.rounding_account.id,
                "auto_diff_label": "Mobile Rounding Difference",
            }
        )
        cls.cheque_bank = cls.env["res.bank"].create({"name": "Mobile Cheque Bank Test"})

    def _new_order(self, invoice_total):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "warehouse_id": self.warehouse.id,
                "so_type_id": self.so_type.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 1.0,
                            "price_unit": invoice_total,
                            "tax_id": [Command.clear()],
                        }
                    )
                ],
            }
        )
        order.action_confirm()
        return order

    def _new_wizard(self, invoice_total, rows):
        order = self._new_order(invoice_total)
        return (
            self.env["sale.advance.payment.inv"]
            .with_context(active_model="sale.order", active_ids=order.ids)
            .create(
                {
                    "advance_payment_method": "delivered",
                    "mobile_payment_line_ids": [Command.create(row) for row in rows],
                }
            )
        )

    def _new_payment_wizard(self, rows):
        return self.env["sale.advance.payment.inv"].create(
            {
                "advance_payment_method": "delivered",
                "mobile_payment_line_ids": [Command.create(row) for row in rows],
            }
        )

    def _new_posted_invoice(self, invoice_total):
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "journal_id": self.sale_journal.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "name": self.product.display_name,
                            "quantity": 1.0,
                            "price_unit": invoice_total,
                            "account_id": self.income_account.id,
                            "tax_ids": [Command.clear()],
                        }
                    )
                ],
            }
        )
        invoice.action_post()
        return invoice

    def _new_posted_credit_note(self, amount):
        credit_note = self.env["account.move"].create(
            {
                "move_type": "out_refund",
                "partner_id": self.partner.id,
                "journal_id": self.sale_journal.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "name": self.product.display_name,
                            "quantity": 1.0,
                            "price_unit": amount,
                            "account_id": self.income_account.id,
                            "tax_ids": [Command.clear()],
                        }
                    )
                ],
            }
        )
        credit_note.action_post()
        return credit_note

    def test_mobile_payment_rows_are_available_on_invoice_wizard(self):
        wizard = self.env["sale.advance.payment.inv"].create(
            {
                "advance_payment_method": "delivered",
                "mobile_payment_line_ids": [
                    Command.create({"payment_type": "bank", "amount": 100.0})
                ],
            }
        )

        self.assertEqual(wizard.mobile_payment_line_ids.payment_type, "bank")

    def test_mobile_wizard_uses_custom_payment_rows_widget(self):
        view = self.env.ref(
            "sale_auto_confirm_invoice.view_sale_advance_payment_inv_inherit_auto_confirm"
        )

        self.assertIn('widget="mobile_mixed_payment_rows"', view.arch_db)
        self.assertNotIn("action_add_bank", view.arch_db)
        self.assertNotIn("action_add_cash", view.arch_db)
        self.assertNotIn("action_add_cheque", view.arch_db)
        self.assertNotIn("action_add_rounding", view.arch_db)

    def test_mobile_payment_amount_widget_uses_two_decimal_precision(self):
        template_path = Path(
            file_path(
                "sale_auto_confirm_invoice/static/src/components/mobile_mixed_payment/mobile_mixed_payment.xml"
            )
        )
        script_path = Path(
            file_path(
                "sale_auto_confirm_invoice/static/src/components/mobile_mixed_payment/mobile_mixed_payment.js"
            )
        )

        self.assertIn("MobileTwoDigitMonetaryField", template_path.read_text())
        self.assertIn("return [16, 2];", script_path.read_text())

    def test_mobile_wizard_warns_and_blocks_rounding_without_account(self):
        self.env.company.auto_diff_account_id = False
        wizard = self._new_wizard(
            1000.0,
            [
                {"payment_type": "bank", "amount": 999.90},
                {"payment_type": "rounding", "amount": 0.10},
            ],
        )

        self.assertTrue(wizard.mobile_account_missing)
        self.assertIn("Rounding Difference Account", wizard.mobile_account_warning)
        self.assertFalse(wizard.mobile_settlement_ready)

    def test_mobile_warehouse_settings_show_rounding_difference_account(self):
        view = self.env.ref(
            "sale_auto_confirm_invoice.res_config_settings_view_form_inherit_sale_auto_confirm_invoice"
        )

        self.assertIn("auto_diff_account_id", view.arch_db)
        self.assertIn("auto_diff_label", view.arch_db)

    def test_totals_allow_any_rounding_amount_when_settlement_matches(self):
        wizard = self._new_wizard(
            1000.0,
            [
                {"payment_type": "cash", "amount": 500.0},
                {"payment_type": "rounding", "amount": 500.0},
            ],
        )

        self.assertEqual(wizard.mobile_invoice_total, 1000.0)
        self.assertEqual(wizard.mobile_actual_payment_total, 500.0)
        self.assertEqual(wizard.mobile_rounding_total, 500.0)
        self.assertEqual(wizard.mobile_balance, 0.0)
        self.assertTrue(wizard.mobile_settlement_ready)
        wizard._validate_mobile_payment_lines(wizard.mobile_invoice_total)

    def test_validation_rejects_settlement_over_invoice_total(self):
        wizard = self._new_wizard(
            1000.0,
            [
                {"payment_type": "bank", "amount": 1000.0},
                {"payment_type": "rounding", "amount": 0.01},
            ],
        )

        with self.assertRaisesRegex(UserError, "exceeds the invoice total"):
            wizard._validate_mobile_payment_lines(wizard.mobile_invoice_total)

    def test_validation_requires_at_least_one_actual_payment(self):
        wizard = self._new_wizard(
            1000.0, [{"payment_type": "rounding", "amount": 1000.0}]
        )

        with self.assertRaisesRegex(UserError, "actual payment"):
            wizard._validate_mobile_payment_lines(wizard.mobile_invoice_total)

    def test_validation_rejects_incomplete_settlement(self):
        wizard = self._new_wizard(
            1000.0, [{"payment_type": "bank", "amount": 999.99}]
        )

        with self.assertRaisesRegex(UserError, "must equal the invoice total"):
            wizard._validate_mobile_payment_lines(wizard.mobile_invoice_total)

    def test_row_amount_must_be_positive(self):
        with self.assertRaisesRegex(UserError, "greater than zero"):
            self._new_wizard(
                1000.0, [{"payment_type": "bank", "amount": -0.01}]
            )

    def test_payment_extension_contracts_are_loaded(self):
        register_fields = self.env["account.payment.register"]._fields

        self.assertIn("deduction_ids", register_fields)
        self.assertIn("wizard_inbound_cheque_lines", register_fields)

    def test_cheque_row_requires_number_and_bank_before_submission(self):
        wizard = self._new_wizard(
            1000.0, [{"payment_type": "cheque", "amount": 1000.0}]
        )

        with self.assertRaisesRegex(UserError, "Cheque Number and Bank"):
            wizard._validate_mobile_payment_lines(wizard.mobile_invoice_total)

    def test_payment_method_routing_separates_cheque_and_manual_lines(self):
        wizard = self._new_payment_wizard(
            [{"payment_type": "cheque", "amount": 1000.0}]
        )

        self.assertEqual(
            wizard._get_payment_method_line_for_journal(
                self.cheque_journal, "cheque"
            ),
            self.cheque_method_line,
        )
        self.assertNotEqual(
            wizard._get_payment_method_line_for_journal(
                self.cheque_journal, "bank"
            ),
            self.cheque_method_line,
        )

    def test_bank_cash_and_rounding_close_receivable_with_writeoff(self):
        invoice = self._new_posted_invoice(150000.10)
        wizard = self._new_payment_wizard(
            [
                {"payment_type": "bank", "amount": 100000.0},
                {"payment_type": "cash", "amount": 50000.0},
                {"payment_type": "rounding", "amount": 0.10},
            ]
        )

        wizard._register_mobile_payment_lines(invoice)

        payments = invoice._get_reconciled_payments()
        self.assertEqual(invoice.amount_residual, 0.0)
        self.assertEqual(len(payments), 1)
        self.assertEqual(payments.journal_id, self.bank_journal)
        cash_writeoff_lines = payments.mapped("move_id.line_ids").filtered(
            lambda line: line.name == "CASH Payment"
        )
        self.assertEqual(len(cash_writeoff_lines), 1)
        self.assertEqual(cash_writeoff_lines.debit - cash_writeoff_lines.credit, 50000.0)
        rounding_lines = payments.mapped("move_id.line_ids").filtered(
            lambda line: line.account_id == self.rounding_account
        )
        self.assertEqual(len(rounding_lines), 1)
        self.assertEqual(rounding_lines.debit - rounding_lines.credit, 0.10)

    def test_mobile_payment_lines_can_partially_pay_invoice(self):
        invoice = self._new_posted_invoice(1000.0)
        wizard = self._new_payment_wizard(
            [{"payment_type": "bank", "amount": 400.0}]
        )

        wizard._register_mobile_payment_lines(invoice)

        payments = invoice._get_reconciled_payments()
        self.assertEqual(len(payments), 1)
        self.assertEqual(payments.amount, 400.0)
        self.assertAlmostEqual(invoice.amount_residual, 600.0)
        self.assertEqual(invoice.payment_state, "partial")

    def test_cheque_payment_attaches_inbound_cheque_and_waits_for_validation(self):
        invoice = self._new_posted_invoice(1000.0)
        wizard = self._new_payment_wizard(
            [
                {
                    "payment_type": "cheque",
                    "amount": 1000.0,
                    "cheque_number": "CHQ-1000",
                    "cheque_bank_id": self.cheque_bank.id,
                    "cheque_branch": "Main",
                }
            ]
        )

        wizard._register_mobile_payment_lines(invoice)

        payment = invoice._get_reconciled_payments()
        self.assertEqual(payment.payment_method_line_id, self.cheque_method_line)
        self.assertEqual(payment.inbound_cheque_lines.cheque_id, "CHQ-1000")
        self.assertEqual(invoice.payment_state, "in_payment")

    def test_mobile_invoice_action_creates_invoice_without_payment(self):
        order = self._new_order(150000.10)
        wizard = (
            self.env["sale.advance.payment.inv"]
            .with_context(active_model="sale.order", active_ids=order.ids)
            .create({"advance_payment_method": "delivered"})
        )

        wizard.action_create_invoice_mobile()

        invoice = order.invoice_ids
        self.assertEqual(len(invoice), 1)
        self.assertEqual(invoice.state, "posted")
        self.assertAlmostEqual(invoice.amount_residual, 150000.10)
        self.assertEqual(invoice.payment_state, "not_paid")
        self.assertEqual(order.van_sales_payment_state, "not_paid")

    def test_sale_order_receive_payment_action_opens_mobile_payment_wizard(self):
        wizard = self._new_wizard(
            1000.0, [{"payment_type": "bank", "amount": 1000.0}]
        )
        wizard.action_create_invoice_mobile()

        action = wizard.sale_order_ids.action_receive_van_sale_payment()

        self.assertEqual(action["res_model"], "sale.advance.payment.inv")
        self.assertEqual(action["target"], "new")
        self.assertEqual(action["context"]["active_model"], "sale.order")
        self.assertEqual(action["context"]["active_ids"], wizard.sale_order_ids.ids)
        self.assertTrue(action["context"]["default_mobile_receive_payment_only"])
        self.assertTrue(action["context"]["default_mobile_payment_invoice_ids"])

    def test_sale_order_mobile_payment_wizard_can_apply_customer_credit_note(self):
        wizard = self._new_wizard(
            1000.0, [{"payment_type": "bank", "amount": 1000.0}]
        )
        wizard.action_create_invoice_mobile()
        order = wizard.sale_order_ids
        invoice = order.invoice_ids
        credit_note = self._new_posted_credit_note(250.0)

        action = order.action_receive_van_sale_payment()
        payment_wizard = (
            self.env["sale.advance.payment.inv"]
            .with_context(action["context"])
            .create(
                {
                    "advance_payment_method": "delivered",
                    "mobile_payment_line_ids": [
                        Command.create({"payment_type": "bank", "amount": 750.0})
                    ],
                }
            )
        )
        credit_line = payment_wizard.mobile_credit_note_line_ids.filtered(
            lambda line: line.move_id == credit_note
        )
        self.assertTrue(credit_line)

        credit_line.is_selected = True
        credit_line.amount = 250.0
        self.assertAlmostEqual(payment_wizard.mobile_credit_note_total, 250.0)
        self.assertAlmostEqual(payment_wizard.mobile_balance, 0.0)

        payment_wizard.action_receive_mobile_payment()
        payment = invoice._get_reconciled_payments()

        self.assertAlmostEqual(payment.amount, 750.0)
        credit_note_payment_lines = payment.move_id.line_ids.filtered(
            lambda line: line.name == "Credit Note %s" % credit_note.name
            and line.account_id == credit_line.account_id
        )
        self.assertEqual(len(credit_note_payment_lines), 1)
        self.assertAlmostEqual(
            credit_note_payment_lines.debit - credit_note_payment_lines.credit,
            250.0,
        )
        self.assertAlmostEqual(invoice.amount_residual, 0.0)
        self.assertAlmostEqual(credit_note.amount_residual, 0.0)

    def test_sale_order_mobile_payment_wizard_can_apply_credit_note_with_writeoff(self):
        wizard = self._new_wizard(
            10000.0, [{"payment_type": "bank", "amount": 10000.0}]
        )
        wizard.action_create_invoice_mobile()
        order = wizard.sale_order_ids
        invoice = order.invoice_ids
        credit_note = self._new_posted_credit_note(2500.0)

        action = order.action_receive_van_sale_payment()
        payment_wizard = (
            self.env["sale.advance.payment.inv"]
            .with_context(action["context"])
            .create(
                {
                    "advance_payment_method": "delivered",
                    "mobile_payment_line_ids": [
                        Command.create({"payment_type": "cash", "amount": 7000.0}),
                        Command.create({"payment_type": "bank", "amount": 400.0}),
                        Command.create({"payment_type": "rounding", "amount": 100.0}),
                    ],
                }
            )
        )
        credit_line = payment_wizard.mobile_credit_note_line_ids.filtered(
            lambda line: line.move_id == credit_note
        )
        self.assertTrue(credit_line)

        credit_line.is_selected = True
        credit_line.amount = 2500.0
        self.assertAlmostEqual(payment_wizard.mobile_actual_payment_total, 7400.0)
        self.assertAlmostEqual(payment_wizard.mobile_credit_note_total, 2500.0)
        self.assertAlmostEqual(payment_wizard.mobile_rounding_total, 100.0)
        self.assertAlmostEqual(payment_wizard.mobile_balance, 0.0)

        payment_wizard.action_receive_mobile_payment()
        payment = invoice._get_reconciled_payments()

        self.assertAlmostEqual(payment.amount, 7000.0)
        credit_note_payment_lines = payment.move_id.line_ids.filtered(
            lambda line: line.name == "Credit Note %s" % credit_note.name
            and line.account_id == credit_line.account_id
        )
        self.assertEqual(len(credit_note_payment_lines), 1)
        self.assertAlmostEqual(
            credit_note_payment_lines.debit - credit_note_payment_lines.credit,
            2500.0,
        )
        self.assertAlmostEqual(invoice.amount_residual, 0.0)
        self.assertAlmostEqual(credit_note.amount_residual, 0.0)

    def test_sale_order_mobile_payment_wizard_can_partially_apply_credit_note(self):
        wizard = self._new_wizard(
            10000.0, [{"payment_type": "bank", "amount": 10000.0}]
        )
        wizard.action_create_invoice_mobile()
        order = wizard.sale_order_ids
        invoice = order.invoice_ids
        credit_note = self._new_posted_credit_note(2500.0)

        action = order.action_receive_van_sale_payment()
        payment_wizard = (
            self.env["sale.advance.payment.inv"]
            .with_context(action["context"])
            .create(
                {
                    "advance_payment_method": "delivered",
                    "mobile_payment_line_ids": [
                        Command.create({"payment_type": "bank", "amount": 5000.0})
                    ],
                }
            )
        )
        credit_line = payment_wizard.mobile_credit_note_line_ids.filtered(
            lambda line: line.move_id == credit_note
        )
        self.assertTrue(credit_line)

        credit_line.is_selected = True
        credit_line.amount = 2500.0
        self.assertAlmostEqual(payment_wizard.mobile_actual_payment_total, 5000.0)
        self.assertAlmostEqual(payment_wizard.mobile_credit_note_total, 2500.0)
        self.assertAlmostEqual(payment_wizard.mobile_balance, 2500.0)

        payment_wizard.action_receive_mobile_payment()
        payment = invoice._get_reconciled_payments()

        self.assertAlmostEqual(payment.amount, 5000.0)
        credit_note_payment_lines = payment.move_id.line_ids.filtered(
            lambda line: line.name == "Credit Note %s" % credit_note.name
            and line.account_id == credit_line.account_id
        )
        self.assertEqual(len(credit_note_payment_lines), 1)
        self.assertAlmostEqual(
            credit_note_payment_lines.debit - credit_note_payment_lines.credit,
            2500.0,
        )
        self.assertAlmostEqual(invoice.amount_residual, 2500.0)
        self.assertAlmostEqual(credit_note.amount_residual, 0.0)

    def test_sale_order_mobile_payment_wizard_can_apply_credit_note_only(self):
        wizard = self._new_wizard(
            1000.0, [{"payment_type": "bank", "amount": 1000.0}]
        )
        wizard.action_create_invoice_mobile()
        order = wizard.sale_order_ids
        invoice = order.invoice_ids
        credit_note = self._new_posted_credit_note(1000.0)

        action = order.action_receive_van_sale_payment()
        payment_wizard = (
            self.env["sale.advance.payment.inv"]
            .with_context(action["context"])
            .create({"advance_payment_method": "delivered"})
        )
        credit_line = payment_wizard.mobile_credit_note_line_ids.filtered(
            lambda line: line.move_id == credit_note
        )
        credit_line.is_selected = True
        credit_line.amount = 1000.0

        payment_wizard.action_receive_mobile_payment()

        self.assertFalse(invoice._get_reconciled_payments())
        self.assertAlmostEqual(invoice.amount_residual, 0.0)
        self.assertAlmostEqual(credit_note.amount_residual, 0.0)

    def test_custom_invoice_posting_paths_do_not_commit_mid_transaction(self):
        wizard_source = inspect.getsource(type(self.env["sale.advance.payment.inv"])._create_invoices)
        order_source = inspect.getsource(type(self.env["sale.order"])._create_invoices)

        self.assertNotIn("self.env.cr.commit()", wizard_source)
        self.assertNotIn("self.env.cr.commit()", order_source)
