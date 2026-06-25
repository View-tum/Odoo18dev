# Mobile Mixed Payment Create Invoice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add tablet-friendly Quick Payment Rows to Mobile Warehouse invoice creation so one customer invoice can be paid immediately by Bank, Cash, Cheque, and a rounding write-off without over-entering the invoice total.

**Architecture:** Extend only `sale_auto_confirm_invoice` with a transient child-line model and a Mobile Warehouse wizard UI. Each Bank, Cash, or Cheque line creates one standard inbound payment through `account.payment.register.action_create_payments()`; the summed Rounding lines become a multi-deduction write-off on the final actual payment. The invoice creation, payment posting, cheque attachment, and reconciliation must remain one atomic Odoo transaction, which requires removing the custom mid-transaction commits already present in this flow.

**Tech Stack:** Odoo 18 Enterprise Python ORM, transient wizard models, XML view inheritance, `account.payment.register`, `account_payment_multi_deduction`, `account_payment_auto_difference`, `cheque_management`, Odoo `TransactionCase`.

---

## Current Integration Constraints

- Preserve existing uncommitted work in `sale_auto_confirm_invoice`, `cheque_management`, and `account_payment_auto_difference`; implement on top of it and do not reset those files.
- Modify custom addons only. Do not edit `server/odoo/addons`.
- Use the existing visible UI entry point: Sales order `Create Invoice` popup for Mobile Warehouse.
- Use list control create buttons instead of new JavaScript for `+ Bank`, `+ Cash`, `+ Cheque`, and `+ ปัดเศษ`.
- Invoke `account.payment.register.action_create_payments()`, not its private `_create_payments()` shortcut, because `cheque_management` persists cheque detail records in its public action override.
- Remove `self.env.cr.commit()` from the custom invoice creation paths touched by this feature. The quick-payment transaction must roll back fully when amount, journal, cheque, or reconciliation validation fails.

## File Structure

- Create: `custom/goldmints_addon-main/sale_auto_confirm_invoice/models/mobile_payment_line.py`
  - Owns transient row fields, route display, row-level amount and cheque validation.
- Modify: `custom/goldmints_addon-main/sale_auto_confirm_invoice/models/__init__.py`
  - Registers the transient row model.
- Modify: `custom/goldmints_addon-main/sale_auto_confirm_invoice/models/sale_advance_payment_inv.py`
  - Owns parent totals, validation, payment-register orchestration, write-off attachment, and paid action.
- Modify: `custom/goldmints_addon-main/sale_auto_confirm_invoice/models/sale_order.py`
  - Removes the explicit transaction commit from invoice auto-posting.
- Modify: `custom/goldmints_addon-main/sale_auto_confirm_invoice/views/sale_make_invoice_advance_views.xml`
  - Replaces the single mobile payment selector with editable Quick Payment Rows and totals.
- Create: `custom/goldmints_addon-main/sale_auto_confirm_invoice/security/ir.model.access.csv`
  - Allows invoice users to edit the transient child rows.
- Modify: `custom/goldmints_addon-main/sale_auto_confirm_invoice/__manifest__.py`
  - Adds accounting/cheque dependencies and loads security data.
- Create: `custom/goldmints_addon-main/sale_auto_confirm_invoice/tests/__init__.py`
- Create: `custom/goldmints_addon-main/sale_auto_confirm_invoice/tests/test_mobile_mixed_payment.py`
  - Covers totals, mixed payment creation, cheque persistence, write-off, rollback, and non-mobile isolation.

### Task 1: Establish Module Dependencies And Test Fixture

**Files:**
- Modify: `custom/goldmints_addon-main/sale_auto_confirm_invoice/__manifest__.py`
- Create: `custom/goldmints_addon-main/sale_auto_confirm_invoice/tests/__init__.py`
- Create: `custom/goldmints_addon-main/sale_auto_confirm_invoice/tests/test_mobile_mixed_payment.py`

- [ ] **Step 1: Add explicit runtime dependencies needed by the approved flow**

Update the `depends` list and security load point in `__manifest__.py`:

```python
"depends": [
    "sale_management",
    "account",
    "account_payment_auto_difference",
    "cheque_management",
],
"data": [
    "security/ir.model.access.csv",
    "views/res_config_settings_views.xml",
    "views/sale_make_invoice_advance_views.xml",
],
```

- [ ] **Step 2: Add the tests package entrypoint**

Create `tests/__init__.py`:

```python
from . import test_mobile_mixed_payment
```

- [ ] **Step 3: Write a failing test fixture for a Mobile Warehouse sale invoice wizard**

Create `tests/test_mobile_mixed_payment.py` with a fixture that prepares journals, configured accounts, one invoiceable sale order, and a helper to construct quick-payment rows:

```python
from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestMobileMixedPayment(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.partner = cls.env.ref("base.res_partner_12")
        cls.product = cls.env.ref("product.product_product_3")
        cls.currency = cls.company.currency_id
        cls.sale_journal = cls.env["account.journal"].search(
            [("type", "=", "sale"), ("company_id", "=", cls.company.id)],
            limit=1,
        )
        cls.receipt_account = cls.env["account.account"].search(
            [("account_type", "=", "asset_current"), ("company_ids", "in", cls.company.id)],
            limit=1,
        )
        cls.cash_journal = cls.env["account.journal"].create(
            {"name": "Mobile Cash", "code": "MCAS", "type": "cash", "company_id": cls.company.id}
        )
        cls.bank_journal = cls.env["account.journal"].create(
            {"name": "Mobile Bank", "code": "MBNK", "type": "bank", "company_id": cls.company.id}
        )
        cls.cheque_journal = cls.env["account.journal"].create(
            {"name": "Mobile Cheque", "code": "MCHQ", "type": "bank", "company_id": cls.company.id}
        )
        cls.cash_journal.inbound_payment_method_line_ids[:1].payment_account_id = cls.receipt_account
        cls.bank_journal.inbound_payment_method_line_ids[:1].payment_account_id = cls.receipt_account
        cls.cheque_method = cls.cheque_journal.inbound_payment_method_line_ids[:1]
        cls.cheque_method.payment_account_id = cls.receipt_account
        cls.cheque_journal.is_cheque_incoming = True
        cls.cheque_method.is_cheque_incoming_line = True
        cls.company.write(
            {
                "mobile_cash_journal_id": cls.cash_journal.id,
                "mobile_bank_transfer_journal_id": cls.bank_journal.id,
                "mobile_cheque_journal_id": cls.cheque_journal.id,
                "auto_diff_account_id": cls.env["account.account"].search(
                    [("account_type", "=", "expense"), ("company_ids", "in", cls.company.id)],
                    limit=1,
                ).id,
                "auto_diff_label": "Rounding Difference",
            }
        )
        cls.warehouse = cls.env["stock.warehouse"].create(
            {"name": "Mobile Warehouse Test", "code": "MWT", "company_id": cls.company.id}
        )

    def _new_order(self, amount):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "warehouse_id": self.warehouse.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 1.0,
                            "price_unit": amount,
                            "tax_id": False,
                        }
                    )
                ],
            }
        )
        order.action_confirm()
        order.order_line.qty_delivered = 1.0
        return order

    def _new_wizard(self, order, rows):
        return self.env["sale.advance.payment.inv"].with_context(
            active_model="sale.order", active_ids=order.ids
        ).create(
            {
                "advance_payment_method": "delivered",
                "mobile_payment_line_ids": [Command.create(row) for row in rows],
            }
        )

    def test_mixed_payment_rows_model_is_available(self):
        order = self._new_order(150000.10)
        wizard = self._new_wizard(order, [{"payment_type": "bank", "amount": 100000.0}])
        self.assertEqual(wizard.mobile_payment_line_ids.payment_type, "bank")
```

- [ ] **Step 4: Run the module test to prove the new row API is missing**

Run:

```powershell
& '.\.venv\Scripts\python.exe' '.\server\odoo-bin' -c '.\server\odoo.conf' -d test_sale_auto_confirm_invoice_mixed_payment -i sale_auto_confirm_invoice --test-enable --test-tags /sale_auto_confirm_invoice --stop-after-init
```

Expected: FAIL because `mobile_payment_line_ids` and its transient model do not yet exist.

### Task 2: Add Transient Quick Payment Rows And Parent Totals

**Files:**
- Create: `custom/goldmints_addon-main/sale_auto_confirm_invoice/models/mobile_payment_line.py`
- Modify: `custom/goldmints_addon-main/sale_auto_confirm_invoice/models/__init__.py`
- Modify: `custom/goldmints_addon-main/sale_auto_confirm_invoice/models/sale_advance_payment_inv.py`
- Create: `custom/goldmints_addon-main/sale_auto_confirm_invoice/security/ir.model.access.csv`
- Test: `custom/goldmints_addon-main/sale_auto_confirm_invoice/tests/test_mobile_mixed_payment.py`

- [ ] **Step 1: Extend the failing tests with totals and over-total validation**

Add these tests:

```python
    def test_quick_payment_totals_allow_large_rounding_when_total_matches(self):
        order = self._new_order(1000.0)
        wizard = self._new_wizard(
            order,
            [
                {"payment_type": "cash", "amount": 500.0},
                {"payment_type": "rounding", "amount": 500.0},
            ],
        )
        self.assertEqual(wizard.mobile_actual_payment_total, 500.0)
        self.assertEqual(wizard.mobile_rounding_total, 500.0)
        self.assertEqual(wizard.mobile_balance, 0.0)
        wizard._validate_mobile_payment_lines(wizard.mobile_invoice_total)

    def test_quick_payment_totals_block_over_invoice_total(self):
        order = self._new_order(1000.0)
        wizard = self._new_wizard(
            order,
            [
                {"payment_type": "bank", "amount": 1000.0},
                {"payment_type": "rounding", "amount": 0.01},
            ],
        )
        with self.assertRaisesRegex(UserError, "เกินยอดใบแจ้งหนี้"):
            wizard._validate_mobile_payment_lines(wizard.mobile_invoice_total)

    def test_quick_payment_requires_actual_receipt_row(self):
        order = self._new_order(1000.0)
        wizard = self._new_wizard(order, [{"payment_type": "rounding", "amount": 1000.0}])
        with self.assertRaises(UserError):
            wizard._validate_mobile_payment_lines(wizard.mobile_invoice_total)
```

- [ ] **Step 2: Run tests to verify the parent fields and validation are missing**

Run the command from Task 1 Step 4.

Expected: FAIL on missing `mobile_actual_payment_total`, `mobile_rounding_total`, and `_validate_mobile_payment_lines`.

- [ ] **Step 3: Create the transient child-line model**

Create `models/mobile_payment_line.py`:

```python
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleAdvancePaymentInvMobileLine(models.TransientModel):
    _name = "sale.advance.payment.inv.mobile.line"
    _description = "Mobile Invoice Payment Line"
    _order = "sequence, id"

    wizard_id = fields.Many2one(
        "sale.advance.payment.inv", required=True, ondelete="cascade"
    )
    sequence = fields.Integer(default=10)
    payment_type = fields.Selection(
        [
            ("bank", "Bank"),
            ("cash", "Cash"),
            ("cheque", "Cheque"),
            ("rounding", "ปัดเศษ"),
        ],
        required=True,
        default="cash",
    )
    amount = fields.Monetary(required=True, currency_field="currency_id")
    currency_id = fields.Many2one(related="wizard_id.currency_id", readonly=True)
    route_name = fields.Char(compute="_compute_route_name")
    cheque_number = fields.Char()
    cheque_bank_id = fields.Many2one("res.bank")
    cheque_branch = fields.Char()
    cheque_date = fields.Date(default=fields.Date.context_today)

    @api.depends("payment_type", "wizard_id.sale_order_ids.company_id")
    def _compute_route_name(self):
        for line in self:
            company = line.wizard_id.sale_order_ids.company_id[:1] or line.wizard_id.company_id
            routes = {
                "cash": company.mobile_cash_journal_id.display_name,
                "bank": company.mobile_bank_transfer_journal_id.display_name,
                "cheque": company.mobile_cheque_journal_id.display_name,
                "rounding": company.auto_diff_account_id.display_name,
            }
            line.route_name = routes.get(line.payment_type) or _("Not configured")

    @api.constrains("amount")
    def _check_positive_amount(self):
        for line in self:
            if line.amount <= 0:
                raise UserError(_("Payment row amount must be greater than zero."))
```

- [ ] **Step 4: Register model and access rights**

Add to `models/__init__.py`:

```python
from . import mobile_payment_line
```

Create `security/ir.model.access.csv`:

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_sale_advance_payment_inv_mobile_line_user,sale.advance.payment.inv.mobile.line user,model_sale_advance_payment_inv_mobile_line,sales_team.group_sale_salesman,1,1,1,0
```

- [ ] **Step 5: Add parent total fields and validation**

Add fields and validation methods to `models/sale_advance_payment_inv.py`:

```python
    mobile_payment_line_ids = fields.One2many(
        "sale.advance.payment.inv.mobile.line", "wizard_id", string="Receive Payment"
    )
    mobile_invoice_total = fields.Monetary(
        compute="_compute_mobile_payment_totals", currency_field="currency_id"
    )
    mobile_actual_payment_total = fields.Monetary(
        compute="_compute_mobile_payment_totals", currency_field="currency_id"
    )
    mobile_rounding_total = fields.Monetary(
        compute="_compute_mobile_payment_totals", currency_field="currency_id"
    )
    mobile_settlement_total = fields.Monetary(
        compute="_compute_mobile_payment_totals", currency_field="currency_id"
    )
    mobile_balance = fields.Monetary(
        compute="_compute_mobile_payment_totals", currency_field="currency_id"
    )
    mobile_amount_exceeded = fields.Boolean(compute="_compute_mobile_payment_totals")
    mobile_settlement_ready = fields.Boolean(compute="_compute_mobile_payment_totals")

    @api.depends("amount_to_invoice", "mobile_payment_line_ids.amount", "mobile_payment_line_ids.payment_type")
    def _compute_mobile_payment_totals(self):
        for wizard in self:
            wizard.mobile_invoice_total = wizard.amount_to_invoice
            actual_lines = wizard.mobile_payment_line_ids.filtered(
                lambda line: line.payment_type != "rounding"
            )
            rounding_lines = wizard.mobile_payment_line_ids.filtered(
                lambda line: line.payment_type == "rounding"
            )
            wizard.mobile_actual_payment_total = sum(actual_lines.mapped("amount"))
            wizard.mobile_rounding_total = sum(rounding_lines.mapped("amount"))
            wizard.mobile_settlement_total = (
                wizard.mobile_actual_payment_total + wizard.mobile_rounding_total
            )
            wizard.mobile_balance = (
                wizard.mobile_invoice_total - wizard.mobile_settlement_total
            )
            wizard.mobile_amount_exceeded = (
                wizard.currency_id.compare_amounts(wizard.mobile_settlement_total, wizard.mobile_invoice_total) > 0
                if wizard.currency_id
                else wizard.mobile_settlement_total > wizard.mobile_invoice_total
            )
            wizard.mobile_settlement_ready = bool(actual_lines) and (
                wizard.currency_id.compare_amounts(wizard.mobile_settlement_total, wizard.mobile_invoice_total) == 0
                if wizard.currency_id
                else wizard.mobile_settlement_total == wizard.mobile_invoice_total
            )

    def _validate_mobile_payment_lines(self, invoice_total):
        self.ensure_one()
        currency = self.currency_id or self.company_id.currency_id
        actual_lines = self.mobile_payment_line_ids.filtered(
            lambda line: line.payment_type != "rounding"
        )
        rounding_lines = self.mobile_payment_line_ids.filtered(
            lambda line: line.payment_type == "rounding"
        )
        if not actual_lines:
            raise UserError(_("Please add at least one Bank, Cash, or Cheque payment row."))
        settlement_total = sum(self.mobile_payment_line_ids.mapped("amount"))
        comparison = currency.compare_amounts(settlement_total, invoice_total)
        if comparison > 0:
            raise UserError(
                _("ยอดรับชำระรวมและยอดปัดเศษเกินยอดใบแจ้งหนี้ กรุณาตรวจสอบยอดก่อนสร้างใบแจ้งหนี้")
            )
        if comparison < 0:
            raise UserError(_("Payment rows must equal the invoice total before receiving payment."))
        if rounding_lines and not self._get_target_company().auto_diff_account_id:
            raise UserError(_("Please configure the Default Auto Difference Account first."))
```

- [ ] **Step 6: Run the totals tests**

Run the command from Task 1 Step 4.

Expected: row model and validation tests PASS.

### Task 3: Create Multiple Payments, Cheque Clearing, And Rounding Write-Off

**Files:**
- Modify: `custom/goldmints_addon-main/sale_auto_confirm_invoice/models/sale_advance_payment_inv.py`
- Test: `custom/goldmints_addon-main/sale_auto_confirm_invoice/tests/test_mobile_mixed_payment.py`

- [ ] **Step 1: Write failing accounting-flow tests**

Add tests:

```python
    def test_bank_cash_and_rounding_create_real_payments_and_writeoff(self):
        order = self._new_order(150000.10)
        wizard = self._new_wizard(
            order,
            [
                {"payment_type": "bank", "amount": 100000.0},
                {"payment_type": "cash", "amount": 50000.0},
                {"payment_type": "rounding", "amount": 0.10},
            ],
        )
        wizard.action_create_invoice_mobile()
        invoice = order.invoice_ids.filtered(lambda move: move.move_type == "out_invoice")[:1]
        payments = invoice.matched_payment_ids
        self.assertEqual(invoice.payment_state, "paid")
        self.assertEqual(len(payments), 2)
        self.assertEqual(set(payments.mapped("journal_id")), self.bank_journal | self.cash_journal)
        difference_lines = payments.move_id.line_ids.filtered(
            lambda line: line.account_id == self.company.auto_diff_account_id
        )
        self.assertEqual(sum(difference_lines.mapped("debit")), 0.10)

    def test_cheque_receipt_creates_inbound_cheque_and_pays_invoice(self):
        order = self._new_order(5000.0)
        wizard = self._new_wizard(
            order,
            [
                {
                    "payment_type": "cheque",
                    "amount": 5000.0,
                    "cheque_number": "CHQ-001",
                    "cheque_bank_id": self.env["res.bank"].create({"name": "Test Bank"}).id,
                    "cheque_branch": "BKK",
                    "cheque_date": fields.Date.today(),
                }
            ],
        )
        wizard.action_create_invoice_mobile()
        invoice = order.invoice_ids.filtered(lambda move: move.move_type == "out_invoice")[:1]
        payment = invoice.matched_payment_ids[:1]
        self.assertEqual(invoice.payment_state, "paid")
        self.assertEqual(payment.inbound_cheque_lines.cheque_id, "CHQ-001")
        self.assertEqual(payment.journal_id, self.cheque_journal)
```

- [ ] **Step 2: Run the tests to verify single-method processing cannot satisfy them**

Run the command from Task 1 Step 4.

Expected: FAIL because the current wizard still routes through one `mobile_payment_method` and does not use the row collection.

- [ ] **Step 3: Replace single-method routing with row-aware orchestration**

Refactor `action_create_invoice_mobile()` and add row helpers:

```python
    def action_create_invoice_mobile(self):
        self.ensure_one()
        if not self.is_mobile_warehouse:
            return self.create_invoices()
        self._validate_mobile_payment_lines(self.mobile_invoice_total)
        invoices = self._create_invoices(self.sale_order_ids)
        posted_invoices = invoices.filtered(lambda move: move.state == "posted")
        actual_total = sum(posted_invoices.mapped("amount_residual"))
        self._validate_mobile_payment_lines(actual_total)
        self._register_mobile_payment_lines(posted_invoices)
        return self.sale_order_ids.action_view_invoice(invoices=invoices)

    def _get_journal_for_mobile_line(self, line):
        company = self._get_target_company()
        journals = {
            "cash": company.mobile_cash_journal_id,
            "bank": company.mobile_bank_transfer_journal_id,
            "cheque": company.mobile_cheque_journal_id,
        }
        journal = journals.get(line.payment_type)
        if not journal:
            raise UserError(_("Please configure a journal for payment type %s.") % line.payment_type)
        if journal.company_id != company:
            raise UserError(_("The selected Mobile Warehouse journal belongs to another company."))
        return journal

    def _get_actual_mobile_lines(self):
        return self.mobile_payment_line_ids.filtered(
            lambda line: line.payment_type != "rounding"
        ).sorted(key=lambda line: (line.sequence, line.id))
```

- [ ] **Step 4: Implement one payment-register execution per actual row**

Add payment registration helpers. Use the public action so cheque extensions attach persistent inbound cheque rows:

```python
    def _register_mobile_payment_lines(self, invoices):
        self.ensure_one()
        payments = self.env["account.payment"]
        actual_lines = self._get_actual_mobile_lines()
        rounding_total = sum(
            self.mobile_payment_line_ids.filtered(
                lambda line: line.payment_type == "rounding"
            ).mapped("amount")
        )
        final_line = actual_lines[-1]
        for line in actual_lines:
            payments |= self._register_single_mobile_payment(
                invoices,
                line,
                rounding_total if line == final_line else 0.0,
            )
        unpaid = invoices.filtered(lambda invoice: invoice.payment_state not in ("paid", "in_payment"))
        if unpaid:
            raise UserError(_("Mobile payment was created but the invoice is not fully paid."))
        return payments

    def _register_single_mobile_payment(self, invoices, line, writeoff_amount):
        journal = self._get_journal_for_mobile_line(line)
        method_line = self._get_payment_method_line_for_journal(journal)
        context = {
            **self.env.context,
            "active_model": "account.move",
            "active_ids": invoices.ids,
            "active_id": invoices[:1].id,
            "skip_caba_zero_cleanup": True,
            "skip_mobile_caba_adjustments": True,
            "no_cash_basis": True,
        }
        values = {
            "journal_id": journal.id,
            "payment_method_line_id": method_line.id,
            "amount": line.amount,
        }
        if writeoff_amount:
            company = self._get_target_company()
            values.update(
                {
                    "payment_difference_handling": "reconcile_multi_deduct",
                    "deduction_ids": [
                        Command.create(
                            {
                                "account_id": company.auto_diff_account_id.id,
                                "name": company.auto_diff_label or _("Difference"),
                                "amount": writeoff_amount,
                                "analytic_distribution": company.auto_diff_analytic_distribution or {},
                                "is_open": False,
                            }
                        )
                    ],
                }
            )
        register = self.env["account.payment.register"].with_context(context).create(values)
        if line.payment_type == "cheque":
            self._prepare_mobile_cheque_register_line(register, line)
        action = register.with_context(context).action_create_payments()
        payments = register._get_created_payment_records(action)
        if not payments:
            raise UserError(_("Mobile payment could not be created for %s.") % line.payment_type)
        return payments

    def _prepare_mobile_cheque_register_line(self, register, line):
        if not line.cheque_number or not line.cheque_bank_id or not line.cheque_date:
            raise UserError(_("Please fill in Cheque Number, Bank, and Cheque Date."))
        register.wizard_inbound_cheque_lines = [
            Command.create(
                {
                    "cheque_id": line.cheque_number,
                    "bank_account_id": line.cheque_bank_id.id,
                    "branch": line.cheque_branch or "",
                    "date": line.cheque_date,
                    "amount": line.amount,
                }
            )
        ]
```

- [ ] **Step 5: Remove the previous single-method mobile payment and manual reconciliation path**

Delete or make unreachable the existing `mobile_payment_method`-driven routing, `_register_mobile_payments()` fallback logic, and manual reconciliation branch once all tests invoke `_register_mobile_payment_lines()`. Retain unrelated down payment account and invoice-date behavior.

- [ ] **Step 6: Run accounting-flow tests**

Run the command from Task 1 Step 4.

Expected: Bank/Cash/Rounding and Cheque tests PASS with paid invoices and persistent cheque lines.

### Task 4: Restore Transaction Atomicity And Test Rollback

**Files:**
- Modify: `custom/goldmints_addon-main/sale_auto_confirm_invoice/models/sale_advance_payment_inv.py`
- Modify: `custom/goldmints_addon-main/sale_auto_confirm_invoice/models/sale_order.py`
- Test: `custom/goldmints_addon-main/sale_auto_confirm_invoice/tests/test_mobile_mixed_payment.py`

- [ ] **Step 1: Add a failing rollback test**

Add a test that posts no invoice if cheque validation fails:

```python
    def test_invalid_cheque_does_not_leave_posted_invoice(self):
        order = self._new_order(5000.0)
        wizard = self._new_wizard(
            order,
            [{"payment_type": "cheque", "amount": 5000.0}],
        )
        with self.assertRaises(UserError):
            wizard.action_create_invoice_mobile()
        self.assertFalse(order.invoice_ids.filtered(lambda invoice: invoice.state == "posted"))
```

- [ ] **Step 2: Run the rollback test to expose the explicit commit risk**

Run the command from Task 1 Step 4.

Expected: FAIL or leave a posted invoice when the existing custom `self.env.cr.commit()` is reached before cheque failure.

- [ ] **Step 3: Remove mid-transaction commits from custom invoice posting**

In both custom posting overrides, retain `action_post()` and remove only explicit `self.env.cr.commit()` calls:

```python
        if draft_moves:
            try:
                draft_moves.action_post()
            except UserError:
                pass
```

Apply this to:

- `models/sale_advance_payment_inv.py::_create_invoices`
- `models/sale_order.py::_create_invoices`

- [ ] **Step 4: Ensure missing configuration is validated before invoice creation**

Before `_create_invoices()` is invoked by `action_create_invoice_mobile()`, validate every actual row journal, every cheque field, and the rounding account:

```python
    def _validate_mobile_payment_configuration(self):
        self.ensure_one()
        company = self._get_target_company()
        for line in self._get_actual_mobile_lines():
            self._get_journal_for_mobile_line(line)
            if line.payment_type == "cheque":
                if not line.cheque_number or not line.cheque_bank_id or not line.cheque_date:
                    raise UserError(_("Please fill in Cheque Number, Bank, and Cheque Date."))
        if self.mobile_rounding_total and not company.auto_diff_account_id:
            raise UserError(_("Please configure the Default Auto Difference Account first."))
```

Call it before invoice creation:

```python
        self._validate_mobile_payment_lines(self.mobile_invoice_total)
        self._validate_mobile_payment_configuration()
        invoices = self._create_invoices(self.sale_order_ids)
```

- [ ] **Step 5: Run rollback and accounting tests**

Run the command from Task 1 Step 4.

Expected: PASS; invalid cheque/configuration raises without a persistent posted invoice.

### Task 5: Render Quick Payment Rows In The Existing Tablet Wizard

**Files:**
- Modify: `custom/goldmints_addon-main/sale_auto_confirm_invoice/views/sale_make_invoice_advance_views.xml`
- Test: `custom/goldmints_addon-main/sale_auto_confirm_invoice/tests/test_mobile_mixed_payment.py`

- [ ] **Step 1: Add a view load test**

Add:

```python
    def test_mobile_invoice_wizard_view_contains_quick_payment_rows(self):
        view = self.env.ref(
            "sale_auto_confirm_invoice.view_sale_advance_payment_inv_inherit_auto_confirm"
        )
        architecture = view.arch_db
        self.assertIn("mobile_payment_line_ids", architecture)
        self.assertIn("Add Bank", architecture)
        self.assertIn("Add Cheque", architecture)
        self.assertNotIn("mobile_payment_method", architecture)
```

- [ ] **Step 2: Run the view test to verify it fails under the single-selector UI**

Run the command from Task 1 Step 4.

Expected: FAIL because the current view still renders `mobile_payment_method`.

- [ ] **Step 3: Replace the mobile single-method block with standard editable list controls**

Update the mobile-only portion of `views/sale_make_invoice_advance_views.xml`:

```xml
<group string="Receive Payment" invisible="not is_mobile_warehouse">
    <group>
        <field name="mobile_invoice_total" readonly="1"/>
        <field name="mobile_actual_payment_total" readonly="1"/>
    </group>
    <group>
        <field name="mobile_rounding_total" readonly="1"/>
        <field name="mobile_balance" readonly="1"/>
    </group>
    <field name="mobile_payment_line_ids" nolabel="1" colspan="4">
        <list editable="bottom">
            <control>
                <create string="Add Bank" context="{'default_payment_type': 'bank'}"/>
                <create string="Add Cash" context="{'default_payment_type': 'cash'}"/>
                <create string="Add Cheque" context="{'default_payment_type': 'cheque'}"/>
                <create string="Add ปัดเศษ" context="{'default_payment_type': 'rounding'}"/>
            </control>
            <field name="sequence" widget="handle"/>
            <field name="payment_type" readonly="1"/>
            <field name="amount" sum="Total"/>
            <field name="route_name" readonly="1"/>
            <field name="cheque_number" invisible="payment_type != 'cheque'" required="payment_type == 'cheque'"/>
            <field name="cheque_bank_id" invisible="payment_type != 'cheque'" required="payment_type == 'cheque'"/>
            <field name="cheque_branch" invisible="payment_type != 'cheque'"/>
            <field name="cheque_date" invisible="payment_type != 'cheque'" required="payment_type == 'cheque'"/>
        </list>
    </field>
    <div class="alert alert-danger" role="alert" invisible="not mobile_amount_exceeded">
        ยอดรับชำระรวมและยอดปัดเศษเกินยอดใบแจ้งหนี้ กรุณาตรวจสอบยอดก่อนสร้างใบแจ้งหนี้
    </div>
</group>
```

Include hidden fields needed by expressions:

```xml
<field name="mobile_amount_exceeded" invisible="1"/>
<field name="mobile_settlement_ready" invisible="1"/>
```

Rename the mobile button to match its behavior:

```xml
<button name="action_create_invoice_mobile" type="object"
        string="Create Invoice &amp; Receive Payment"
        class="btn-primary"
        invisible="not is_mobile_warehouse or not mobile_settlement_ready"/>
```

- [ ] **Step 4: Run view and Python tests**

Run the command from Task 1 Step 4.

Expected: PASS with the XML view loading successfully under Odoo 18 expression syntax.

### Task 6: Validate Existing Behavior And Perform UI Verification

**Files:**
- Test: `custom/goldmints_addon-main/sale_auto_confirm_invoice/tests/test_mobile_mixed_payment.py`

- [ ] **Step 1: Add non-mobile and down-payment preservation tests**

Add:

```python
    def test_non_mobile_wizard_does_not_require_payment_rows(self):
        order = self._new_order(1000.0)
        order.warehouse_id = self.env["stock.warehouse"].search(
            [("id", "!=", self.warehouse.id), ("company_id", "=", self.company.id)],
            limit=1,
        )
        wizard = self.env["sale.advance.payment.inv"].with_context(
            active_model="sale.order", active_ids=order.ids
        ).create({"advance_payment_method": "delivered"})
        self.assertFalse(wizard.is_mobile_warehouse)

    def test_missing_rounding_account_blocks_before_accounting_documents(self):
        self.company.auto_diff_account_id = False
        order = self._new_order(1000.0)
        wizard = self._new_wizard(
            order,
            [
                {"payment_type": "cash", "amount": 900.0},
                {"payment_type": "rounding", "amount": 100.0},
            ],
        )
        with self.assertRaises(UserError):
            wizard.action_create_invoice_mobile()
        self.assertFalse(order.invoice_ids)
```

- [ ] **Step 2: Run the complete module test suite**

Run:

```powershell
& '.\.venv\Scripts\python.exe' '.\server\odoo-bin' -c '.\server\odoo.conf' -d test_sale_auto_confirm_invoice_mixed_payment -u sale_auto_confirm_invoice --test-enable --test-tags /sale_auto_confirm_invoice --stop-after-init
```

Expected: `0 failed, 0 error(s)` for `sale_auto_confirm_invoice` tests.

- [ ] **Step 3: Upgrade the module in a local verification database and inspect tablet UI**

Run:

```powershell
& '.\.venv\Scripts\python.exe' '.\server\odoo-bin' -c '.\server\odoo.conf' -d GoldMints_Uat_Manu -u sale_auto_confirm_invoice --stop-after-init
```

Then use the local UI at `http://localhost:8811`:

1. Open a Mobile Warehouse Sales Order.
2. Click the existing `Create Invoice` action.
3. Confirm the popup displays Quick Payment Rows and the four add actions.
4. Add Bank `100000.00`, Cash `50000.00`, and ปัดเศษ `0.10` against a matching invoice amount.
5. Confirm Balance displays `0.00`.
6. Confirm the paid action creates two payments plus one write-off line.
7. Repeat with a Cheque row and verify the invoice shows Paid while the payment contains inbound cheque details.

Expected: tablet layout follows the approved Quick Payment Rows mockup and journal items follow the approved accounting entries.

- [ ] **Step 4: Review the final diff without discarding pre-existing modifications**

Run:

```powershell
git diff -- custom/goldmints_addon-main/sale_auto_confirm_invoice
git diff -- custom/goldmints_addon-main/account_payment_auto_difference custom/goldmints_addon-main/cheque_management
```

Expected: feature changes are confined to `sale_auto_confirm_invoice`; existing related-module changes remain intact and are used through their public behavior.

## Execution Commit Guidance

The target module already contains uncommitted changes before this implementation begins. During execution:

- Do not reset or revert any pre-existing changes.
- Keep a record of exactly which hunks are added for Quick Payment Rows.
- Do not create feature commits containing pre-existing user changes unless the user confirms those changes should be committed together.
- The design commit `c81c604` is already isolated and does not include the dirty custom-module files.
