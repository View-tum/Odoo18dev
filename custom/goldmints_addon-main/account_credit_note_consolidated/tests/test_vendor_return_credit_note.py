from odoo import fields
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestVendorReturnCreditNote(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        partner_vals = {"name": "Vendor Return CN Test"}
        if "approval_state" in cls.env["res.partner"]._fields:
            partner_vals["approval_state"] = "approved"
        cls.vendor = cls.env["res.partner"].create(partner_vals)
        cls.expense_account = cls.env["account.account"].create({
            "name": "Vendor Return CN Expense",
            "code": "VRCNEXP",
            "account_type": "expense",
        })
        cls.payable_account = cls.env["account.account"].create({
            "name": "Vendor Return CN Payable",
            "code": "VRCNPAY",
            "account_type": "liability_payable",
            "reconcile": True,
        })
        cls.vendor.property_account_payable_id = cls.payable_account
        cls.product = cls.env["product.product"].create({
            "name": "Vendor Return CN Product",
            "is_storable": True,
            "standard_price": 40.0,
            "property_account_expense_id": cls.expense_account.id,
            "supplier_taxes_id": [(6, 0, [])],
        })
        cls.warehouse = cls.env["stock.warehouse"].search([
            ("company_id", "=", cls.env.company.id),
        ], limit=1)

    def _create_receipt_with_bill(self, quantity=3.0, price_unit=100.0, tax_ids=None):
        tax_ids = tax_ids or []
        receipt_vals = {
            "partner_id": self.vendor.id,
            "picking_type_id": self.warehouse.in_type_id.id,
            "location_id": self.env.ref("stock.stock_location_suppliers").id,
            "location_dest_id": self.warehouse.lot_stock_id.id,
            "move_ids": [
                (0, 0, {
                    "product_id": self.product.id,
                    "name": self.product.display_name,
                    "product_uom_qty": quantity,
                    "product_uom": self.product.uom_id.id,
                    "location_id": self.env.ref("stock.stock_location_suppliers").id,
                    "location_dest_id": self.warehouse.lot_stock_id.id,
                })
            ],
        }
        if "invoice_reference" in self.env["stock.picking"]._fields:
            receipt_vals["invoice_reference"] = "VENDOR-RETURN-CN-TEST"
        if "invoice_date" in self.env["stock.picking"]._fields:
            receipt_vals["invoice_date"] = fields.Date.today()
        receipt = self.env["stock.picking"].with_context(skip_invoice_constraint=True).create(receipt_vals)
        receipt.move_ids.write({
            "quantity": quantity,
            "picked": True,
            "state": "done",
        })
        receipt.with_context(skip_invoice_constraint=True).write({"state": "done"})

        bill = self.env["account.move"].create({
            "move_type": "in_invoice",
            "partner_id": self.vendor.id,
            "invoice_date": fields.Date.today(),
            "invoice_line_ids": [
                (0, 0, {
                    "product_id": self.product.id,
                    "name": self.product.display_name,
                    "quantity": quantity,
                    "price_unit": price_unit,
                    "account_id": self.expense_account.id,
                    "tax_ids": [(6, 0, tax_ids)],
                })
            ],
        })
        bill.invoice_date = fields.Date.today()
        if "tax_invoice_ids" in bill._fields:
            for tax_invoice in bill.tax_invoice_ids:
                tax_invoice.tax_invoice_number = "TAX-RETURN-CN"
                tax_invoice.tax_invoice_date = fields.Date.today()
        bill.action_post()
        return receipt, bill

    def _create_return(self, receipt, quantity):
        source_move = receipt.move_ids[:1]
        return_vals = {
            "partner_id": self.vendor.id,
            "picking_type_id": self.warehouse.out_type_id.id,
            "location_id": self.warehouse.lot_stock_id.id,
            "location_dest_id": self.env.ref("stock.stock_location_suppliers").id,
            "return_id": receipt.id,
            "move_ids": [
                (0, 0, {
                    "product_id": self.product.id,
                    "name": self.product.display_name,
                    "product_uom_qty": quantity,
                    "quantity": quantity,
                    "picked": True,
                    "product_uom": self.product.uom_id.id,
                    "location_id": self.warehouse.lot_stock_id.id,
                    "location_dest_id": self.env.ref("stock.stock_location_suppliers").id,
                    "origin_returned_move_id": source_move.id,
                })
            ],
        }
        if "invoice_reference" in self.env["stock.picking"]._fields:
            return_vals["invoice_reference"] = receipt.invoice_reference
        if "invoice_date" in self.env["stock.picking"]._fields:
            return_vals["invoice_date"] = receipt.invoice_date
        return_picking = self.env["stock.picking"].with_context(skip_invoice_constraint=True).create(return_vals)
        return_picking.move_ids.write({
            "quantity": quantity,
            "picked": True,
            "state": "done",
        })
        return_picking.with_context(skip_invoice_constraint=True).write({"state": "done"})
        return return_picking

    def test_vendor_credit_note_can_select_multiple_return_pickings(self):
        receipt, bill = self._create_receipt_with_bill()
        first_return = self._create_return(receipt, 1.0)
        second_return = self._create_return(receipt, 1.0)

        reversal = self.env["account.move.reversal"].with_context(
            active_model="account.move",
            active_ids=bill.ids,
        ).create({
            "reason": "Vendor returns",
            "date": fields.Date.today(),
            "journal_id": bill.journal_id.id,
        })
        reversal.return_picking_ids = [(6, 0, (first_return | second_return).ids)]
        action = reversal.refund_moves()
        credit_note = self.env["account.move"].browse(action["res_id"])

        self.assertEqual(credit_note.move_type, "in_refund")
        self.assertEqual(set(credit_note.return_picking_ids.ids), set((first_return | second_return).ids))
        return_lines = credit_note.invoice_line_ids.filtered("return_stock_move_id")
        self.assertEqual(len(return_lines), 2)
        self.assertEqual(set(return_lines.mapped("return_picking_id").ids), set((first_return | second_return).ids))
        self.assertEqual(return_lines.mapped("quantity"), [1.0, 1.0])
        self.assertEqual(return_lines.mapped("price_unit"), [100.0, 100.0])
        self.assertEqual(first_return.vendor_credit_note_state, "draft")
        self.assertEqual(second_return.vendor_credit_note_state, "draft")

        credit_note.invoice_date = fields.Date.today()
        credit_note.action_post()
        self.assertEqual(first_return.vendor_credit_note_state, "posted")
        self.assertEqual(second_return.vendor_credit_note_state, "posted")

    def test_vendor_credit_note_can_select_multiple_return_pickings_with_tax(self):
        tax = self.env["account.tax"].create({
            "name": "Vendor Return CN Tax 7%",
            "amount_type": "percent",
            "type_tax_use": "purchase",
            "amount": 7.0,
        })
        receipt, bill = self._create_receipt_with_bill(tax_ids=[tax.id])
        first_return = self._create_return(receipt, 1.0)
        second_return = self._create_return(receipt, 1.0)

        reversal = self.env["account.move.reversal"].with_context(
            active_model="account.move",
            active_ids=bill.ids,
        ).create({
            "reason": "Vendor returns with tax",
            "date": fields.Date.today(),
            "journal_id": bill.journal_id.id,
        })
        reversal.return_picking_ids = [(6, 0, (first_return | second_return).ids)]
        action = reversal.refund_moves()
        credit_note = self.env["account.move"].browse(action["res_id"])
        credit_note.invoice_date = fields.Date.today()
        if "tax_invoice_ids" in credit_note._fields:
            for tax_invoice in credit_note.tax_invoice_ids:
                tax_invoice.tax_invoice_number = "TAX-RETURN-CN-CREDIT"
                tax_invoice.tax_invoice_date = fields.Date.today()
        credit_note.action_post()

        return_lines = credit_note.invoice_line_ids.filtered("return_stock_move_id")
        self.assertEqual(len(return_lines), 2)
        self.assertAlmostEqual(credit_note.amount_untaxed, 200.0, places=2)
        self.assertAlmostEqual(credit_note.amount_tax, 14.0, places=2)
        self.assertAlmostEqual(credit_note.amount_total, 214.0, places=2)
        self.assertEqual(return_lines.mapped("tax_ids"), tax)
        self.assertEqual(first_return.vendor_credit_note_state, "posted")
        self.assertEqual(second_return.vendor_credit_note_state, "posted")

    def test_vendor_credit_note_can_select_multiple_return_pickings_with_partial_quantity(self):
        receipt, bill = self._create_receipt_with_bill(quantity=5.0, price_unit=80.0)
        first_return = self._create_return(receipt, 1.0)
        second_return = self._create_return(receipt, 2.0)

        reversal = self.env["account.move.reversal"].with_context(
            active_model="account.move",
            active_ids=bill.ids,
        ).create({
            "reason": "Vendor partial returns",
            "date": fields.Date.today(),
            "journal_id": bill.journal_id.id,
        })
        reversal.return_picking_ids = [(6, 0, (first_return | second_return).ids)]
        action = reversal.refund_moves()
        credit_note = self.env["account.move"].browse(action["res_id"])
        credit_note.invoice_date = fields.Date.today()
        credit_note.action_post()

        return_lines = credit_note.invoice_line_ids.filtered("return_stock_move_id")
        self.assertEqual(return_lines.mapped("quantity"), [1.0, 2.0])
        self.assertAlmostEqual(credit_note.amount_untaxed, 240.0, places=2)
        self.assertAlmostEqual(credit_note.amount_total, 240.0, places=2)
        self.assertEqual(first_return.vendor_credit_note_state, "posted")
        self.assertEqual(second_return.vendor_credit_note_state, "posted")
