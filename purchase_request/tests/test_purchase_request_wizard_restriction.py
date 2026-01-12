
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError

class TestPurchaseRequestWizardRestriction(TransactionCase):

    def setUp(self):
        super(TestPurchaseRequestWizardRestriction, self).setUp()
        self.purchase_request_model = self.env['purchase.request']
        self.purchase_request_line_model = self.env['purchase.request.line']
        self.wizard_model = self.env['purchase.request.line.make.purchase.order']
        self.wizard_item_model = self.env['purchase.request.line.make.purchase.order.item']
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

    def test_wizard_quantity_restriction(self):
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
        
        # 2. Create Wizard
        ctx = {'active_model': 'purchase.request.line', 'active_ids': [pr_line.id]}
        wizard = self.wizard_model.with_context(ctx).create({
            'supplier_id': self.partner.id,
        })
        
        # 3. Try to create an item with quantity > 10
        with self.assertRaises(UserError):
            self.wizard_item_model.create({
                'wiz_id': wizard.id,
                'line_id': pr_line.id,
                'product_id': self.product.id,
                'product_uom_id': self.product.uom_id.id,
                'name': 'Test Item',
                'product_qty': 11.0, # Exceeds 10.0
            })

        # 4. Create an item with quantity <= 10 (Should succeed)
        item = self.wizard_item_model.create({
            'wiz_id': wizard.id,
            'line_id': pr_line.id,
            'product_id': self.product.id,
            'product_uom_id': self.product.uom_id.id,
            'name': 'Test Item',
            'product_qty': 10.0,
        })
        self.assertTrue(item)
