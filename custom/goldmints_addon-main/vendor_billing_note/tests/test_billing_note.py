from odoo.tests import TransactionCase, tagged
from odoo.exceptions import UserError, ValidationError
from odoo import fields


@tagged('post_install', '-at_install')
class TestVendorBillingNote(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        vendor_vals = {'name': 'Test Supplier'}
        if 'approval_state' in cls.env['res.partner']._fields:
            vendor_vals['approval_state'] = 'approved'
        cls.vendor = cls.env['res.partner'].create(vendor_vals)
        product_vals = {'name': 'Test Service Product', 'type': 'service'}
        if 'is_storable' in cls.env['product.product']._fields:
            product_vals['is_storable'] = False
        cls.product = cls.env['product.product'].create(product_vals)
        cls.product.product_tmpl_id.purchase_method = 'purchase'
        cls.payable_account = cls.env['account.account'].create({
            'name': 'Test Payable Account',
            'code': 'TPAYABLE',
            'account_type': 'liability_payable',
            'reconcile': True,
        })
        cls.expense_account = cls.env['account.account'].create({
            'name': 'Test Expense Account',
            'code': 'TEXPENSE',
            'account_type': 'expense',
        })
        cls.outstanding_account = cls.env['account.account'].create({
            'name': 'Test Outstanding Payment Account',
            'code': 'TOUTPAY',
            'account_type': 'asset_cash',
            'reconcile': True,
        })
        cls.analytic_account = cls.env['account.analytic.account'].create({
            'name': 'Test Billing Note Analytic',
            'plan_id': cls.env['account.analytic.plan'].search([], limit=1).id,
        })
        cls.vendor.property_account_payable_id = cls.payable_account
        other_vendor_vals = {
            'name': 'Other Test Supplier',
            'property_account_payable_id': cls.payable_account.id,
        }
        if 'approval_state' in cls.env['res.partner']._fields:
            other_vendor_vals['approval_state'] = 'approved'
        cls.other_vendor = cls.env['res.partner'].create(other_vendor_vals)
        cls.journal = cls.env['account.journal'].create({
            'name': 'Test Purchase Journal',
            'code': 'TPJ',
            'type': 'purchase',
        })
        cls.payment_journal = cls.env['account.journal'].create({
            'name': 'Test Payment Journal',
            'code': 'TPAYJ',
            'type': 'cash',
            'default_account_id': cls.outstanding_account.id,
        })
        cls.outbound_payment_method = cls.payment_journal.outbound_payment_method_line_ids[:1]
        cls.outbound_payment_method.payment_account_id = cls.outstanding_account
        if 'pmt_ap_journal_id' in cls.env.company._fields:
            cls.env.company.pmt_ap_journal_id = cls.payment_journal
        if 'pmt_ap_payment_method_id' in cls.env.company._fields:
            cls.env.company.pmt_ap_payment_method_id = cls.outbound_payment_method
        cls.usd = cls.env.ref('base.USD')

    def _create_vendor_move(self, move_type, amount):
        move = self.env['account.move'].create({
            'move_type': move_type,
            'partner_id': self.vendor.id,
            'journal_id': self.journal.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [
                (0, 0, {
                    'name': move_type,
                    'quantity': 1.0,
                    'price_unit': amount,
                    'account_id': self.expense_account.id,
                })
            ],
        })
        if 'tax_invoice_ids' in move._fields:
            move.tax_invoice_ids.write({
                'tax_invoice_number': 'TEST-TAX-PO-STATUS',
                'tax_invoice_date': fields.Date.today(),
            })
        move.action_post()
        return move

    def _create_vendor_move_from_po(self, po, move_type, amount):
        return self.env['account.move'].create({
            'move_type': move_type,
            'partner_id': po.partner_id.id,
            'journal_id': self.journal.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [
                (0, 0, {
                    'name': move_type,
                    'product_id': po.order_line.product_id.id,
                    'quantity': 1.0,
                    'price_unit': amount,
                    'account_id': self.expense_account.id,
                    'purchase_line_id': po.order_line.id,
                    'tax_ids': [(6, 0, [])],
                })
            ],
        })

    def _confirm_purchase_order(self, po):
        po.button_confirm()
        if po.state == 'to approve' and hasattr(po, 'button_approve'):
            po.button_approve()
        return po

    def _receive_purchase_order(self, po):
        pickings = po.picking_ids.filtered(lambda picking: picking.state not in ('cancel', 'done'))
        if not pickings:
            for line in po.order_line:
                if line.qty_received_method == 'manual':
                    line.qty_received = line.product_qty
            po.order_line.flush_recordset(['qty_received'])
            po.invalidate_recordset(['order_line'])
            return po
        for picking in pickings:
            if 'invoice_reference' in picking._fields:
                picking.invoice_reference = 'TEST-INV-REF'
            if 'invoice_date' in picking._fields:
                picking.invoice_date = fields.Date.today()
            for move in picking.move_ids:
                if 'quantity' in move._fields:
                    move.quantity = move.product_uom_qty
                if 'picked' in move._fields:
                    move.picked = True
            result = picking.button_validate()
            if isinstance(result, dict) and result.get('res_model') == 'stock.immediate.transfer':
                wizard = self.env[result['res_model']].with_context(**result.get('context', {})).browse(result['res_id'])
                wizard.process()
        po.order_line.flush_recordset(['qty_received'])
        po.invalidate_recordset(['order_line'])
        return po

    def _create_purchase_order(self, quantity=5.0, price_unit=100.0, partner=None):
        po = self.env['purchase.order'].create({
            'partner_id': (partner or self.vendor).id,
            'order_line': [
                (0, 0, {
                    'product_id': self.product.id,
                    'name': self.product.name,
                    'product_qty': quantity,
                    'product_uom': self.product.uom_po_id.id,
                    'price_unit': price_unit,
                    'taxes_id': [(6, 0, [])],
                    'date_planned': fields.Datetime.now(),
                })
            ]
        })
        self._confirm_purchase_order(po)
        self._receive_purchase_order(po)
        return po

    def _create_unreceived_purchase_order(self, product, quantity=1.0, price_unit=100.0):
        po = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'order_line': [
                (0, 0, {
                    'product_id': product.id,
                    'name': product.name,
                    'product_qty': quantity,
                    'product_uom': product.uom_po_id.id,
                    'price_unit': price_unit,
                    'taxes_id': [(6, 0, [])],
                    'date_planned': fields.Datetime.now(),
                })
            ],
        })
        self._confirm_purchase_order(po)
        return po

    def _create_billing_note_from_po(self, po, quantity=None):
        line = po.order_line[0]
        quantity = quantity if quantity is not None else line.qty_received
        return self.env['vendor.billing.note'].create({
            'partner_id': po.partner_id.id,
            'line_ids': [
                (0, 0, {
                    'purchase_line_id': line.id,
                    'name': line.name,
                    'quantity': quantity,
                    'price_unit': line.price_unit,
                    'tax_ids': [(6, 0, line.taxes_id.ids)],
                })
            ],
        })

    def _open_payable_lines(self, moves):
        valid_types = self.env['account.payment']._get_valid_payment_account_types()
        return moves.line_ids.filtered(
            lambda line: line.account_type in valid_types
            and not line.reconciled
            and not line.company_currency_id.is_zero(line.amount_residual)
        )

    def test_storable_po_billing_note_flow(self):
        po = self._create_purchase_order(quantity=5.0, price_unit=100.0)

        action = po.action_create_billing_note()
        billing_note = self.env['vendor.billing.note'].browse(action['res_id'])

        self.assertEqual(billing_note.amount_untaxed, 500.0)
        self.assertEqual(billing_note.amount_total, 500.0)

        billing_note.action_confirm()
        self.assertEqual(billing_note.state, 'confirmed')

        action = billing_note.action_create_bill()
        bill = self.env['account.move'].browse(action['res_id'])
        self.assertTrue(bill.exists())

        if bill.state == 'draft':
            bill.invoice_date = fields.Date.today()
            if 'tax_invoice_ids' in bill._fields:
                for tax_inv in bill.tax_invoice_ids:
                    tax_inv.tax_invoice_number = 'TAX-12345'
                    tax_inv.tax_invoice_date = fields.Date.today()
            bill.action_post()

        self.assertEqual(billing_note.state, 'billed')

        payment_action = billing_note.action_register_payment()
        self.assertEqual(payment_action['res_model'], 'account.payment.register')
        self.assertEqual(payment_action['context']['active_model'], 'account.move.line')
        self.assertEqual(
            set(payment_action['context']['active_ids']),
            set(self._open_payable_lines(bill).ids)
        )

    def test_fixed_asset_po_is_billable_before_receipt(self):
        category = self.env['product.category'].create({
            'name': 'Fixed Asset Billing Note Category',
            'is_fixed_asset': True,
        })
        product = self.env['product.product'].create({
            'name': 'Fixed Asset Billing Note Product',
            'type': 'consu',
            'categ_id': category.id,
        })
        po = self._create_unreceived_purchase_order(product, quantity=1.0, price_unit=600000.0)
        line = po.order_line[0]

        self.assertEqual(line.qty_received, 0.0)
        self.assertAlmostEqual(line._get_billing_note_qty_basis(), 1.0)
        self.assertAlmostEqual(line._get_qty_to_billing_note(), 1.0)
        self.assertTrue(po.is_billing_note_ready)

        wizard = self.env['purchase.order.status.report.wizard'].create({
            'vendor_id': self.vendor.id,
            'date_from': fields.Date.today(),
            'date_to': fields.Date.today(),
        })
        wizard.button_preview()
        po_header = wizard.line_ids.filtered(lambda row: row.order_id == po and row.is_header and row.line_type == 'po')[:1]
        self.assertTrue(po_header)
        self.assertTrue(po_header.is_billable)

        po_header.is_selected = True
        action = wizard.action_create_billing_note()
        billing_note = self.env['vendor.billing.note'].browse(action['res_id'])

        self.assertEqual(billing_note.partner_id, self.vendor)
        self.assertAlmostEqual(billing_note.line_ids.quantity, 1.0)
        self.assertAlmostEqual(billing_note.amount_total, 600000.0)
        line.invalidate_recordset()
        self.assertAlmostEqual(line.qty_billing_noted, 1.0)

    def test_existing_apd_cn_billing_note_net_amount_and_payment_context(self):
        bill = self._create_vendor_move('in_invoice', 100.0)
        credit_note = self._create_vendor_move('in_refund', 25.0)

        billing_note = self.env['vendor.billing.note'].create({
            'partner_id': self.vendor.id,
        })
        billing_note.selected_bill_ids = [(6, 0, (bill | credit_note).ids)]

        self.assertEqual(billing_note.billing_source, 'existing_bills')
        self.assertAlmostEqual(billing_note.amount_vendor_bills, 100.0)
        self.assertAlmostEqual(billing_note.amount_credit_notes, 25.0)
        self.assertAlmostEqual(billing_note.amount_net_due, 75.0)

        billing_note.action_confirm()
        self.assertEqual(billing_note.state, 'billed')

        action = billing_note.action_register_payment()
        expected_lines = self._open_payable_lines(bill | credit_note)

        self.assertEqual(action['res_model'], 'account.payment.register')
        self.assertEqual(action['context']['active_model'], 'account.move.line')
        self.assertEqual(set(action['context']['active_ids']), set(expected_lines.ids))
        self.assertEqual(action['context'].get('default_journal_id'), self.payment_journal.id)
        self.assertEqual(action['context'].get('default_payment_method_line_id'), self.outbound_payment_method.id)
        self.assertTrue(action['context'].get('skip_wht_deduct'))

        wizard = (
            self.env['account.payment.register']
            .with_context(**action['context'])
            .create({})
        )
        self.assertEqual(wizard.payment_type, 'outbound')
        self.assertEqual(wizard.journal_id, self.payment_journal)
        self.assertEqual(wizard.payment_method_line_id, self.outbound_payment_method)
        self.assertAlmostEqual(wizard.amount, 75.0)
        self.assertAlmostEqual(wizard.payment_difference, 0.0)

        wizard.action_create_payments()
        (bill | credit_note).invalidate_recordset()
        billing_note.invalidate_recordset()
        self.assertEqual(bill.payment_state, 'paid')
        self.assertEqual(credit_note.payment_state, 'paid')
        self.assertEqual(billing_note.payment_state, 'paid')
        self.assertAlmostEqual(billing_note.amount_residual_net_due, 0.0)

    def test_vendor_bill_and_credit_note_action_creates_billing_note(self):
        bill = self._create_vendor_move('in_invoice', 100.0)
        credit_note = self._create_vendor_move('in_refund', 40.0)

        action = (bill | credit_note).action_create_vendor_billing_note()
        billing_note = self.env['vendor.billing.note'].browse(action['res_id'])

        self.assertEqual(billing_note.partner_id, self.vendor)
        self.assertEqual(set(billing_note.selected_bill_ids.ids), set((bill | credit_note).ids))
        self.assertEqual(billing_note.billing_source, 'existing_bills')
        self.assertAlmostEqual(billing_note.amount_vendor_bills, 100.0)
        self.assertAlmostEqual(billing_note.amount_net_due, 60.0)

        with self.assertRaises(UserError):
            (bill | credit_note).action_create_vendor_billing_note()

    def test_po_status_wizard_shows_po_bills_and_creates_billing_note_from_selected_apd_cn(self):
        po = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'order_line': [
                (0, 0, {
                    'product_id': self.product.id,
                    'name': self.product.name,
                    'product_qty': 5.0,
                    'product_uom': self.product.uom_po_id.id,
                    'price_unit': 100.0,
                    'taxes_id': [(6, 0, [])],
                    'date_planned': fields.Datetime.now(),
                })
            ],
        })
        bill = self._create_vendor_move_from_po(po, 'in_invoice', 100.0)
        credit_note = self._create_vendor_move_from_po(po, 'in_refund', 25.0)

        wizard = self.env['purchase.order.status.report.wizard'].create({
            'vendor_id': self.vendor.id,
            'date_from': fields.Date.today(),
            'date_to': fields.Date.today(),
        })
        wizard.button_preview()

        bill_lines = wizard.line_ids.filtered(lambda line: line.account_move_id in (bill | credit_note))
        self.assertEqual(set(bill_lines.mapped('account_move_id').ids), set((bill | credit_note).ids))
        self.assertTrue(all(line.line_type == 'bill' for line in bill_lines))
        self.assertTrue(all(line.is_billable for line in bill_lines))
        self.assertAlmostEqual(sum(bill_lines.mapped('bill_amount_total')), 75.0)

        wizard.action_select_bill_lines()
        self.assertEqual(set(wizard.line_ids.filtered('is_selected').mapped('account_move_id').ids), set((bill | credit_note).ids))
        action = wizard.action_create_billing_note()
        billing_note = self.env['vendor.billing.note'].browse(action['res_id'])

        self.assertEqual(billing_note.partner_id, self.vendor)
        self.assertEqual(set(billing_note.selected_bill_ids.ids), set((bill | credit_note).ids))
        self.assertEqual(billing_note.billing_source, 'existing_bills')
        self.assertAlmostEqual(billing_note.amount_net_due, 75.0)

        wizard.button_preview()
        billed_lines = wizard.line_ids.filtered(lambda line: line.account_move_id in (bill | credit_note))
        self.assertTrue(all(line.vendor_billing_note_id == billing_note for line in billed_lines))
        self.assertFalse(any(billed_lines.mapped('is_billable')))

    def test_po_status_mixed_po_and_apd_cn_amounts_match_payment(self):
        po = self._create_purchase_order(quantity=2.0, price_unit=100.0)
        bill = self._create_vendor_move_from_po(po, 'in_invoice', 100.0)
        credit_note = self._create_vendor_move_from_po(po, 'in_refund', 30.0)
        for move in bill | credit_note:
            if 'tax_invoice_ids' in move._fields:
                move.tax_invoice_ids.write({
                    'tax_invoice_number': 'TEST-TAX-MIXED-PO-APD-CN',
                    'tax_invoice_date': fields.Date.today(),
                })
            move.action_post()

        wizard = self.env['purchase.order.status.report.wizard'].create({
            'vendor_id': self.vendor.id,
            'date_from': fields.Date.today(),
            'date_to': fields.Date.today(),
        })
        wizard.button_preview()
        po_line = wizard.line_ids.filtered(lambda line: line.order_id == po and line.line_type == 'po' and line.is_header)
        bill_lines = wizard.line_ids.filtered(lambda line: line.account_move_id in (bill | credit_note))
        wizard.line_ids.write({'is_selected': False})
        (po_line[:1] | bill_lines).write({'is_selected': True})

        action = wizard.action_create_billing_note()
        billing_note = self.env['vendor.billing.note'].browse(action['res_id'])

        self.assertEqual(billing_note.billing_source, 'mixed')
        self.assertAlmostEqual(billing_note.amount_total, 300.0)
        self.assertAlmostEqual(billing_note.amount_credit_notes, 30.0)
        self.assertAlmostEqual(billing_note.amount_net_due, 270.0)

        billing_note.action_confirm()
        action = billing_note.action_create_bill()
        generated_bill = self.env['account.move'].browse(action['res_id'])
        if generated_bill.state == 'draft':
            generated_bill.invoice_date = fields.Date.today()
            if 'tax_invoice_ids' in generated_bill._fields:
                generated_bill.tax_invoice_ids.write({
                    'tax_invoice_number': 'TEST-TAX-MIXED-GENERATED',
                    'tax_invoice_date': fields.Date.today(),
                })
            generated_bill.action_post()

        billing_note.invalidate_recordset()
        self.assertAlmostEqual(billing_note.amount_total, 300.0)
        self.assertAlmostEqual(billing_note.amount_net_due, 270.0)

        payment_action = billing_note.action_register_payment()
        wizard = (
            self.env['account.payment.register']
            .with_context(**payment_action['context'])
            .create({})
        )
        self.assertAlmostEqual(wizard.amount, 270.0)
        self.assertAlmostEqual(wizard.payment_difference, 0.0)
        wizard.action_create_payments()
        (bill | credit_note | generated_bill).invalidate_recordset()
        self.assertTrue(all(move.payment_state == 'paid' for move in bill | credit_note | generated_bill))
        self.assertAlmostEqual(billing_note.amount_residual_net_due, 0.0)

    def test_sequence_confirm_empty_and_unlink_state_guards(self):
        billing_note = self.env['vendor.billing.note'].create({
            'partner_id': self.vendor.id,
        })

        self.assertNotEqual(billing_note.name, 'New')
        self.assertEqual(billing_note.billing_source, 'empty')

        with self.assertRaises(UserError):
            billing_note.action_confirm()

        bill = self._create_vendor_move('in_invoice', 50.0)
        billing_note.selected_bill_ids = [(6, 0, bill.ids)]
        billing_note.action_confirm()
        with self.assertRaises(UserError):
            billing_note.unlink()

        billing_note.action_cancel()
        billing_note.unlink()
        self.assertFalse(bill.vendor_billing_note_id)

    def test_selected_bill_validation_rejects_invalid_documents(self):
        valid_bill = self._create_vendor_move('in_invoice', 100.0)
        cancelled_bill = self._create_vendor_move('in_invoice', 80.0)
        cancelled_bill.button_cancel()
        other_vendor_bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.other_vendor.id,
            'journal_id': self.journal.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [
                (0, 0, {
                    'name': 'Other vendor',
                    'quantity': 1.0,
                    'price_unit': 10.0,
                    'account_id': self.expense_account.id,
                })
            ],
        })
        customer_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.vendor.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [
                (0, 0, {
                    'name': 'Customer invoice',
                    'quantity': 1.0,
                    'price_unit': 10.0,
                    'account_id': self.expense_account.id,
                })
            ],
        })
        usd_bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.vendor.id,
            'journal_id': self.journal.id,
            'currency_id': self.usd.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [
                (0, 0, {
                    'name': 'USD bill',
                    'quantity': 1.0,
                    'price_unit': 10.0,
                    'account_id': self.expense_account.id,
                })
            ],
        })
        other_note = self.env['vendor.billing.note'].create({
            'partner_id': self.vendor.id,
        })
        other_note.selected_bill_ids = [(6, 0, valid_bill.ids)]

        checks = [
            cancelled_bill,
            customer_invoice,
            other_vendor_bill,
            valid_bill,
            valid_bill | usd_bill,
        ]
        for bills in checks:
            note = self.env['vendor.billing.note'].create({
                'partner_id': self.vendor.id,
            })
            with self.assertRaises(UserError):
                note.selected_bill_ids = [(6, 0, bills.ids)]

    def test_po_action_creates_billing_note_and_prevents_over_billing(self):
        po = self._create_purchase_order(quantity=5.0, price_unit=120.0)

        self.assertTrue(po.is_billing_note_ready)
        action = po.action_create_billing_note()
        billing_note = self.env['vendor.billing.note'].browse(action['res_id'])

        self.assertEqual(billing_note.partner_id, self.vendor)
        self.assertEqual(billing_note.purchase_ids, po)
        self.assertEqual(billing_note.purchase_count, 1)
        self.assertEqual(billing_note.line_ids.quantity, po.order_line.qty_received)
        self.assertEqual(po.order_line.qty_billing_noted, po.order_line.qty_received)
        self.assertFalse(po.is_billing_note_ready)

        with self.assertRaises(UserError):
            po.action_create_billing_note()

        with self.assertRaises(ValidationError):
            self.env['vendor.billing.note'].create({
                'partner_id': self.vendor.id,
                'line_ids': [
                    (0, 0, {
                        'purchase_line_id': po.order_line.id,
                        'name': po.order_line.name,
                        'quantity': 0.01,
                        'price_unit': po.order_line.price_unit,
                    })
                ],
            })

        billing_note.action_cancel()
        self.assertEqual(po.order_line.qty_billing_noted, 0.0)
        self.assertTrue(po.is_billing_note_ready)

    def test_purchase_request_status_report_creates_billing_note_and_marks_status(self):
        pr = self.env['purchase.request'].create({
            'vendor': self.vendor.id,
            'date_start': fields.Date.today(),
            'line_ids': [
                (0, 0, {
                    'product_id': self.product.id,
                    'name': self.product.name,
                    'product_qty': 5.0,
                    'product_uom_id': self.product.uom_id.id,
                    'unit_cost': 100.0,
                    'estimated_cost': 500.0,
                    'analytic_distribution': {str(self.analytic_account.id): 100.0},
                })
            ],
        })
        po = self._create_purchase_order(quantity=5.0, price_unit=100.0)
        pr.line_ids.purchase_lines = [(6, 0, po.order_line.ids)]

        wizard = self.env['purchase.request.status.report.wizard'].create({
            'company_id': self.env.company.id,
            'vendor_id': self.vendor.id,
            'date_from': fields.Date.today(),
            'date_to': fields.Date.today(),
        })
        report = self.env['report.purchase_request_status_report.pr_status_report']

        line_data = report._get_lines(wizard)[0]
        self.assertEqual(line_data['billing_note_status'], 'ready')
        self.assertAlmostEqual(line_data['qty_received'], 5.0)
        self.assertAlmostEqual(line_data['qty_billing_noted'], 0.0)
        self.assertAlmostEqual(line_data['qty_to_billing_note'], 5.0)

        action = wizard.action_create_billing_note()
        billing_note = self.env['vendor.billing.note'].browse(action['res_id'])

        self.assertEqual(billing_note.partner_id, self.vendor)
        self.assertEqual(billing_note.line_ids.purchase_line_id, po.order_line)
        self.assertAlmostEqual(billing_note.line_ids.quantity, 5.0)

        line_data = report._get_lines(wizard)[0]
        self.assertEqual(line_data['billing_note_status'], 'done')
        self.assertAlmostEqual(line_data['qty_to_billing_note'], 0.0)

    def test_confirmed_po_billing_note_creates_bill_and_updates_state(self):
        po = self._create_purchase_order(quantity=5.0, price_unit=100.0)
        billing_note = self._create_billing_note_from_po(po, quantity=2.0)

        billing_note.action_confirm()
        action = billing_note.action_create_bill()
        bill = self.env['account.move'].browse(action['res_id'])

        self.assertEqual(bill.vendor_billing_note_id, billing_note)
        self.assertEqual(bill.invoice_line_ids.purchase_line_id, po.order_line)
        self.assertEqual(bill.invoice_line_ids.quantity, 2.0)
        self.assertEqual(billing_note.state, 'billed')
        self.assertEqual(billing_note.bill_count, 1)
        self.assertEqual(billing_note.billing_source, 'mixed')
        self.assertAlmostEqual(billing_note.amount_total, 200.0)

        with self.assertRaises(UserError):
            billing_note.action_create_bill()

    def test_consolidated_billing_note_and_create_bill_wizard(self):
        po1 = self._create_purchase_order(quantity=3.0, price_unit=100.0)
        po2 = self._create_purchase_order(quantity=4.0, price_unit=200.0)
        action = (po1 | po2).action_create_consolidated_billing_note()
        billing_note = self.env['vendor.billing.note'].browse(action['res_id'])
        billing_note.action_confirm()

        self.assertEqual(set(billing_note.purchase_ids.ids), set((po1 | po2).ids))

        wizard = self.env['create.bill.wizard'].create({
            'purchase_id': po1.id,
            'billing_note_id': billing_note.id,
            'create_type': 'specific',
        })
        action = wizard.action_confirm()
        first_bill = self.env['account.move'].browse(action['res_id'])

        self.assertEqual(first_bill.invoice_line_ids.purchase_line_id.order_id, po1)
        self.assertEqual(billing_note.state, 'partial_billed')

        wizard_all = self.env['create.bill.wizard'].create({
            'purchase_id': po1.id,
            'billing_note_id': billing_note.id,
            'create_type': 'all',
        })
        wizard_all.action_confirm()

        self.assertEqual(billing_note.state, 'billed')
        self.assertEqual(set(billing_note.bill_ids.invoice_line_ids.purchase_line_id.order_id.ids), set((po1 | po2).ids))

    def test_credit_note_reversal_keeps_billing_note_and_net_due(self):
        bill = self._create_vendor_move('in_invoice', 100.0)
        billing_note = self.env['vendor.billing.note'].create({
            'partner_id': self.vendor.id,
        })
        billing_note.selected_bill_ids = [(6, 0, bill.ids)]
        billing_note.action_confirm()

        reversal = self.env['account.move.reversal'].with_context(
            active_model='account.move',
            active_ids=bill.ids,
        ).create({
            'reason': 'Vendor billing note refund',
            'journal_id': bill.journal_id.id,
            'date': fields.Date.today(),
        })
        action = reversal.reverse_moves()
        credit_note = self.env['account.move'].browse(action.get('res_id'))

        self.assertEqual(credit_note.vendor_billing_note_id, billing_note)
        self.assertIn(credit_note, billing_note.bill_ids)
        self.assertAlmostEqual(billing_note.amount_credit_notes, 100.0)
        self.assertAlmostEqual(billing_note.amount_net_due, 0.0)

    def test_action_views_return_form_for_single_and_list_for_multiple_records(self):
        po = self._create_purchase_order()
        billing_note = self._create_billing_note_from_po(po)
        bill_one = self._create_vendor_move('in_invoice', 10.0)
        bill_two = self._create_vendor_move('in_invoice', 20.0)

        billing_note.selected_bill_ids = [(6, 0, bill_one.ids)]
        purchase_action = billing_note.action_view_purchase_order()
        bill_action = billing_note.action_view_vendor_bills()

        self.assertEqual(purchase_action['view_mode'], 'form')
        self.assertEqual(purchase_action['res_id'], po.id)
        self.assertEqual(bill_action['view_mode'], 'form')
        self.assertEqual(bill_action['res_id'], bill_one.id)

        billing_note.selected_bill_ids = [(6, 0, (bill_one | bill_two).ids)]
        bill_action = billing_note.action_view_vendor_bills()

        self.assertEqual(bill_action['view_mode'], 'list,form')
        self.assertEqual(bill_action['domain'], [('id', 'in', billing_note.bill_ids.ids)])
