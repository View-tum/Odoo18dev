
from odoo.tests.common import TransactionCase

class TestPurchaseRequestRemainingQty(TransactionCase):

    def setUp(self):
        super(TestPurchaseRequestRemainingQty, self).setUp()
        self.purchase_request_model = self.env['purchase.request']
        self.purchase_request_line_model = self.env['purchase.request.line']
        self.wizard_model = self.env['purchase.request.line.make.purchase.order']
        self.purchase_order_model = self.env['purchase.order']
        self.purchase_order_line_model = self.env['purchase.order.line']
        self.product_model = self.env['product.product']
        self.res_partner_model = self.env['res.partner']

        # Create a product
        self.product = self.product_model.create({
            'name': 'Test Product',
            'type': 'product',
            'purchase_method': 'purchase',
        })

        # Create a partner
        self.partner = self.res_partner_model.create({
            'name': 'Test Supplier',
        })

    def test_remaining_quantity_calculation(self):
        # 1. Create a Purchase Request for 10 units
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
        
        # 2. Create a PO for 4 units manually (simulating wizard action)
        po = self.purchase_order_model.create({
            'partner_id': self.partner.id,
        })
        
        po_line = self.purchase_order_line_model.create({
            'order_id': po.id,
            'product_id': self.product.id,
            'product_qty': 4.0,
            'price_unit': 100.0,
            'purchase_request_lines': [(4, pr_line.id)],
        })
        
        # Confirm PO to update purchased_qty
        po.button_confirm()
        
        # Force recompute
        pr_line.invalidate_recordset()
        
        # Check purchased_qty
        self.assertEqual(pr_line.purchased_qty, 4.0, "Purchased Qty should be 4.0")
        
        # Check pending_qty_to_receive
        self.assertEqual(pr_line.pending_qty_to_receive, 6.0, "Pending Qty should be 6.0 (10 - 4)")

        # 3. Open Wizard and check default quantity
        ctx = {'active_model': 'purchase.request.line', 'active_ids': [pr_line.id]}
        wizard = self.wizard_model.with_context(ctx).create({
            'supplier_id': self.partner.id,
        })
        
        # The wizard items are created in default_get or get_items, let's check the item created
        wizard_item = wizard.item_ids[0]
        self.assertEqual(wizard_item.product_qty, 6.0, "Wizard default quantity should be 6.0")
