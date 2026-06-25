from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPurchaseAssetDiscountApportion(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Discount Vendor"})
        cls.asset_account = cls.env["account.account"].create(
            {
                "name": "Asset Discount Test Account",
                "code": "ASTDISC",
                "account_type": "asset_fixed",
            }
        )
        cls.payable_account = cls.env["account.account"].create(
            {
                "name": "Asset Discount Test Payable",
                "code": "ASTPAY",
                "account_type": "liability_payable",
                "reconcile": True,
            }
        )
        cls.partner.property_account_payable_id = cls.payable_account
        cls.purchase_journal = cls.env["account.journal"].create(
            {"name": "Asset Test Purchase", "code": "ATPU", "type": "purchase"}
        )
        cls.tax_country = cls.env.ref("base.th")
        cls.env.company.country_id = cls.tax_country
        cls.env.company.account_fiscal_country_id = cls.tax_country
        cls.purchase_tax_group = cls.env["account.tax.group"].create(
            {"name": "Input VAT Test"}
        )
        cls.purchase_tax = cls.env["account.tax"].create(
            {
                "name": "Input VAT 7%",
                "type_tax_use": "purchase",
                "amount_type": "percent",
                "amount": 7.0,
                "tax_group_id": cls.purchase_tax_group.id,
                "country_id": cls.tax_country.id,
            }
        )
        cls.asset_category = cls.env["product.category"].create(
            {"name": "Asset Discount Test", "is_fixed_asset": True}
        )
        cls.asset_a = cls.env["product.product"].create(
            {
                "name": "Asset A",
                "type": "service",
                "categ_id": cls.asset_category.id,
                "purchase_method": "purchase",
            }
        )
        cls.asset_b = cls.env["product.product"].create(
            {
                "name": "Asset B",
                "type": "service",
                "categ_id": cls.asset_category.id,
                "purchase_method": "purchase",
            }
        )
        cls.discount_product = cls.env["product.product"].create(
            {
                "name": "Asset Discount",
                "type": "service",
                "categ_id": cls.asset_category.id,
                "purchase_method": "purchase",
                "is_apportion_discount": True,
            }
        )

    def _new_purchase_order(self):
        return self.env["purchase.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.asset_a.id,
                            "name": self.asset_a.name,
                            "product_qty": 1.0,
                            "product_uom": self.asset_a.uom_po_id.id,
                            "date_planned": fields.Datetime.now(),
                            "price_unit": 600000.0,
                            "fixed_discount": 60000.0,
                            "discount": 10.0,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "product_id": self.asset_b.id,
                            "name": self.asset_b.name,
                            "product_qty": 1.0,
                            "product_uom": self.asset_b.uom_po_id.id,
                            "date_planned": fields.Datetime.now(),
                            "price_unit": 400000.0,
                            "fixed_discount": 40000.0,
                            "discount": 10.0,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "product_id": self.discount_product.id,
                            "name": self.discount_product.name,
                            "product_qty": 1.0,
                            "product_uom": self.discount_product.uom_po_id.id,
                            "date_planned": fields.Datetime.now(),
                            "price_unit": -4000.0,
                        },
                    ),
                ],
            }
        )

    def test_confirm_preserves_visible_discount_line(self):
        order = self._new_purchase_order()
        asset_lines = order.order_line.filtered(
            lambda line: line.product_id in (self.asset_a | self.asset_b)
        )
        discount_line = order.order_line.filtered(
            lambda line: line.product_id == self.discount_product
        )

        order.button_confirm()

        self.assertEqual(asset_lines[0].fixed_discount, 60000.0)
        self.assertEqual(asset_lines[1].fixed_discount, 40000.0)
        self.assertEqual(discount_line.price_unit, -4000.0)

    def test_bill_asset_values_allocate_visible_discount_line(self):
        bill = self.env["account.move"].new(
            {
                "move_type": "in_invoice",
                "partner_id": self.partner.id,
                "journal_id": self.purchase_journal.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.asset_a.id,
                            "name": self.asset_a.name,
                            "quantity": 1.0,
                            "price_unit": 600000.0,
                            "discount": 10.0,
                            "account_id": self.asset_account.id,
                            "tax_ids": [(6, 0, self.purchase_tax.ids)],
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "product_id": self.asset_b.id,
                            "name": self.asset_b.name,
                            "quantity": 1.0,
                            "price_unit": 400000.0,
                            "discount": 10.0,
                            "account_id": self.asset_account.id,
                            "tax_ids": [(6, 0, self.purchase_tax.ids)],
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "product_id": self.discount_product.id,
                            "name": self.discount_product.name,
                            "quantity": 1.0,
                            "price_unit": -4000.0,
                            "account_id": self.asset_account.id,
                            "tax_ids": [(6, 0, self.purchase_tax.ids)],
                        },
                    ),
                ],
            }
        )
        asset_lines = bill.invoice_line_ids.filtered(
            lambda line: line.product_id in (self.asset_a | self.asset_b)
        )

        asset_a_amount = bill._get_asset_amounts_for_bill_line(asset_lines[0], 1)
        asset_b_amount = bill._get_asset_amounts_for_bill_line(asset_lines[1], 1)

        self.assertEqual(asset_a_amount, [537600.0])
        self.assertEqual(asset_b_amount, [358400.0])
        self.assertNotIn(
            self.discount_product,
            bill._get_asset_creation_lines().mapped("product_id"),
        )

    def test_post_links_apportioned_discount_journal_items_to_each_asset(self):
        bill = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.partner.id,
                "journal_id": self.purchase_journal.id,
                "invoice_date": fields.Date.today(),
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.asset_a.id,
                            "name": self.asset_a.name,
                            "quantity": 1.0,
                            "price_unit": 600000.0,
                            "discount": 10.0,
                            "account_id": self.asset_account.id,
                            "tax_ids": [(6, 0, self.purchase_tax.ids)],
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "product_id": self.asset_b.id,
                            "name": self.asset_b.name,
                            "quantity": 1.0,
                            "price_unit": 400000.0,
                            "discount": 10.0,
                            "account_id": self.asset_account.id,
                            "tax_ids": [(6, 0, self.purchase_tax.ids)],
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "product_id": self.discount_product.id,
                            "name": self.discount_product.name,
                            "quantity": 1.0,
                            "price_unit": -4000.0,
                            "account_id": self.asset_account.id,
                            "tax_ids": [(6, 0, self.purchase_tax.ids)],
                        },
                    ),
                ],
            }
        )

        bill.action_post()

        asset_lines = bill.invoice_line_ids.filtered(
            lambda line: line.product_id in (self.asset_a | self.asset_b)
        )
        discount_lines = bill.invoice_line_ids.filtered(
            lambda line: line.product_id == self.discount_product
        )
        self.assertEqual(len(discount_lines), 2)
        self.assertEqual(sorted(discount_lines.mapped("price_subtotal")), [-2400.0, -1600.0])
        self.assertEqual(sum(discount_lines.mapped("quantity")), 1.0)
        self.assertEqual(bill.amount_untaxed, 896000.0)
        self.assertEqual(bill.amount_tax, 62720.0)
        self.assertEqual(bill.amount_total, 958720.0)
        self.assertEqual(
            sum(bill._get_asset_source_lines(asset_lines[0]).mapped("balance")),
            537600.0,
        )
        self.assertEqual(
            sum(bill._get_asset_source_lines(asset_lines[1]).mapped("balance")),
            358400.0,
        )

    def test_post_links_single_discount_line_to_single_asset(self):
        bill = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.partner.id,
                "journal_id": self.purchase_journal.id,
                "invoice_date": fields.Date.today(),
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.asset_a.id,
                            "name": self.asset_a.name,
                            "quantity": 1.0,
                            "price_unit": 600000.0,
                            "discount": 10.0,
                            "account_id": self.asset_account.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "product_id": self.discount_product.id,
                            "name": self.discount_product.name,
                            "quantity": 1.0,
                            "price_unit": -4000.0,
                            "account_id": self.asset_account.id,
                        },
                    ),
                ],
            }
        )

        bill.action_post()

        asset_line = bill.invoice_line_ids.filtered(
            lambda line: line.product_id == self.asset_a
        )
        discount_lines = bill.invoice_line_ids.filtered(
            lambda line: line.product_id == self.discount_product
        )
        self.assertEqual(len(discount_lines), 1)
        self.assertEqual(
            sum(bill._get_asset_source_lines(asset_line).mapped("balance")),
            536000.0,
        )

    def test_cannot_create_assets_from_draft_bill(self):
        bill = self.env["account.move"].new(
            {
                "move_type": "in_invoice",
                "partner_id": self.partner.id,
                "journal_id": self.purchase_journal.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.asset_a.id,
                            "name": self.asset_a.name,
                            "quantity": 1.0,
                            "price_unit": 600000.0,
                            "account_id": self.asset_account.id,
                        },
                    ),
                ],
            }
        )

        with self.assertRaisesRegex(UserError, "post the vendor bill"):
            bill.action_create_assets_from_bill_lines()
