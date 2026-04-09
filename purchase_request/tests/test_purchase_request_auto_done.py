
from odoo.tests.common import TransactionCase


class TestPurchaseRequestAutoDone(TransactionCase):

    def setUp(self):
        super(TestPurchaseRequestAutoDone, self).setUp()
        self.purchase_request_model = self.env['purchase.request']
        self.purchase_request_line_model = self.env['purchase.request.line']
        self.purchase_order_model = self.env['purchase.order']
        self.purchase_order_line_model = self.env['purchase.order.line']
        self.product_model = self.env['product.product']
        self.res_partner_model = self.env['res.partner']

        # Create a product
        self.product = self.product_model.create({
            'name': 'Test Product',
            'detailed_type': 'product',
            'purchase_method': 'purchase',
        })

        # Create a partner
        self.partner = self.res_partner_model.create({
            'name': 'Test Supplier',
        })

    def test_auto_done_purchase_request(self):
        # 1. Create a Purchase Request
        pr = self.purchase_request_model.create({
            'requested_by': self.env.user.id,
            'picking_type_id': self.env.ref('stock.picking_type_in').id
        })

        pr_line = self.purchase_request_line_model.create({
            'request_id': pr.id,
            'product_id': self.product.id,
            'product_uom_id': self.product.uom_id.id,
            'product_qty': 10.0,
        })

        # Approve the PR
        pr.button_to_approve()
        pr.button_approved()

        self.assertEqual(pr.state, 'approved',
                         "PR should be in approved state")

        # 2. Create a Purchase Order linked to the PR
        po = self.purchase_order_model.create({
            'partner_id': self.partner.id,
        })

        po_line = self.purchase_order_line_model.create({
            'order_id': po.id,
            'product_id': self.product.id,
            'product_qty': 10.0,
            'price_unit': 100.0,
            'purchase_request_lines': [(4, pr_line.id)],
        })

        # 3. Confirm the PO
        po.button_confirm()

        # 4. Check if PR state is 'done'
        self.assertEqual(
            pr.state, 'done', "PR should be in done state after full PO confirmation")

    def test_partial_purchase_request(self):
        # 1. Create a Purchase Request
        pr = self.purchase_request_model.create({
            'requested_by': self.env.user.id,
            'picking_type_id': self.env.ref('stock.picking_type_in').id
        })

        pr_line = self.purchase_request_line_model.create({
            'request_id': pr.id,
            'product_id': self.product.id,
            'product_uom_id': self.product.uom_id.id,
            'product_qty': 10.0,
        })

        # Approve the PR
        pr.button_to_approve()
        pr.button_approved()

        self.assertEqual(pr.state, 'approved',
                         "PR should be in approved state")

        # 2. Create a Purchase Order linked to the PR (Partial Quantity)
        po = self.purchase_order_model.create({
            'partner_id': self.partner.id,
        })

        po_line = self.purchase_order_line_model.create({
            'order_id': po.id,
            'product_id': self.product.id,
            'product_qty': 5.0,
            'price_unit': 100.0,
            'purchase_request_lines': [(4, pr_line.id)],
        })

        # 3. Confirm the PO
        po.button_confirm()

        # 4. Check if PR state is NOT 'done'
        self.assertNotEqual(
            pr.state, 'done', "PR should NOT be in done state after partial PO confirmation")

    def test_auto_done_on_lock(self):
        # 1. Create a Purchase Request
        pr = self.purchase_request_model.create({
            'requested_by': self.env.user.id,
            'picking_type_id': self.env.ref('stock.picking_type_in').id
        })

        pr_line = self.purchase_request_line_model.create({
            'request_id': pr.id,
            'product_id': self.product.id,
            'product_uom_id': self.product.uom_id.id,
            'product_qty': 10.0,
        })

        # Approve the PR
        pr.button_to_approve()
        pr.button_approved()

        # 2. Create a Purchase Order linked to the PR
        po = self.purchase_order_model.create({
            'partner_id': self.partner.id,
        })

        po_line = self.purchase_order_line_model.create({
            'order_id': po.id,
            'product_id': self.product.id,
            'product_qty': 10.0,
            'price_unit': 100.0,
            'purchase_request_lines': [(4, pr_line.id)],
        })

        # 3. Confirm the PO
        po.button_confirm()

        # 4. Lock the PO (button_done)
        po.button_done()

        # 5. Check if PR state is 'done'
        self.assertEqual(
            pr.state, 'done', "PR should be in done state after PO lock")
