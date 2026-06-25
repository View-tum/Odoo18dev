from datetime import date
from unittest.mock import Mock, patch

from odoo import fields
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "account_ocr_local")
class TestAccountOcrLocal(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.env["ir.config_parameter"].sudo()
        cls.income_account = cls.env["account.account"].create({
            "name": "OCR Income",
            "code": "OCRINC",
            "account_type": "income",
        })
        cls.expense_account = cls.env["account.account"].create({
            "name": "OCR Expense",
            "code": "OCREXP",
            "account_type": "expense",
        })
        cls.payable_account = cls.env["account.account"].create({
            "name": "OCR Payable",
            "code": "OCRPAY",
            "account_type": "liability_payable",
            "reconcile": True,
        })
        cls.receivable_account = cls.env["account.account"].create({
            "name": "OCR Receivable",
            "code": "OCRREC",
            "account_type": "asset_receivable",
            "reconcile": True,
        })
        partner_vals = {
            "name": "OCR Vendor",
            "vat": "0105559999999",
            "property_account_payable_id": cls.payable_account.id,
            "property_account_receivable_id": cls.receivable_account.id,
        }
        if "approval_state" in cls.env["res.partner"]._fields:
            partner_vals["approval_state"] = "approved"
        cls.vendor = cls.env["res.partner"].create(partner_vals)
        customer_vals = dict(partner_vals)
        customer_vals.update({
            "name": "OCR Customer By Ref",
            "vat": "0105558888888",
            "ref": "10300",
            "customer_rank": 1,
            "supplier_rank": 0,
        })
        cls.customer_by_ref = cls.env["res.partner"].create(customer_vals)
        cls.product = cls.env["product.product"].create({
            "name": "OCR Product",
            "property_account_expense_id": cls.expense_account.id,
            "property_account_income_id": cls.income_account.id,
            "supplier_taxes_id": [(6, 0, [])],
            "taxes_id": [(6, 0, [])],
        })

    def setUp(self):
        super().setUp()
        self.config.set_param("account_ocr_local.local_ocr_enabled", False)
        self.config.set_param("account_ocr_local.local_ocr_server_url", "http://127.0.0.1:8099")
        self.config.set_param("account_ocr_local.local_ocr_replace_lines", False)
        self.config.set_param("account_ocr_local.local_ocr_confidence_threshold", 0.90)

    def _attachment(self, move, mimetype="application/pdf"):
        return self.env["ir.attachment"].create({
            "name": "ocr-test.pdf",
            "raw": b"%PDF-1.4 test",
            "mimetype": mimetype,
            "res_model": "account.move",
            "res_id": move.id,
        })

    def _bill(self):
        return self.env["account.move"].create({
            "move_type": "in_invoice",
            "partner_id": self.vendor.id,
            "invoice_date": fields.Date.today(),
            "invoice_line_ids": [(0, 0, {
                "name": "Existing Line",
                "quantity": 1.0,
                "price_unit": 50.0,
                "account_id": self.expense_account.id,
            })],
        })

    def _ocr_response(self, confidence=0.98, line_items=None, raw_text="OCR text"):
        parsed_data = {
            "vendor_name": "OCR Vendor",
            "tax_id": "0105559999999",
            "invoice_date": str(fields.Date.today()),
            "invoice_number": "OCR-INV-001",
            "subtotal": 120.0,
            "vat_amount": 0.0,
            "total_amount": 120.0,
            "document_type": "handwritten",
            "line_items": line_items if line_items is not None else [{
                "description": "OCR Product",
                "quantity": 2.0,
                "price_unit": 60.0,
                "product_code": self.product.default_code or "",
                "product_name": self.product.name,
            }],
        }
        if confidence is not None:
            parsed_data["confidence"] = confidence
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "extracted_text": raw_text,
            "parsed_data": parsed_data,
        }
        return response

    def test_local_ocr_is_disabled_by_default(self):
        settings = self.env["res.config.settings"].create({})
        self.assertFalse(settings.local_ocr_enabled)

    def test_account_move_has_auditable_local_ocr_fields(self):
        fields_to_check = {
            "local_ocr_state",
            "local_ocr_confidence",
            "local_ocr_document_type",
            "local_ocr_raw_text",
            "local_ocr_error",
            "local_ocr_attachment_id",
        }
        self.assertTrue(fields_to_check.issubset(self.env["account.move"]._fields))

    @patch("odoo.addons.account_ocr_local.models.account_move.requests.post")
    def test_local_ocr_keeps_existing_lines_unless_replace_is_enabled(self, post):
        post.return_value = self._ocr_response()
        bill = self._bill()
        attachment = self._attachment(bill)

        bill._run_local_ocr(attachment, "http://127.0.0.1:8099")

        self.assertEqual(bill.local_ocr_state, "review")
        self.assertEqual(bill.partner_id, self.vendor)
        self.assertEqual(bill.ref, "OCR-INV-001")
        self.assertEqual(len(bill.invoice_line_ids), 2)
        self.assertIn("Existing Line", bill.invoice_line_ids.mapped("name"))
        ocr_line = bill.invoice_line_ids.filtered(lambda line: line.name == "OCR Product")
        self.assertEqual(ocr_line.account_id, self.expense_account)

    @patch("odoo.addons.account_ocr_local.models.account_move.requests.post")
    def test_local_ocr_low_confidence_requires_review_and_does_not_create_lines(self, post):
        post.return_value = self._ocr_response(confidence=0.50)
        bill = self._bill()
        attachment = self._attachment(bill)
        original_ref = bill.ref
        original_date = bill.invoice_date

        bill._run_local_ocr(attachment, "http://127.0.0.1:8099")

        self.assertEqual(bill.local_ocr_state, "review")
        self.assertEqual(bill.local_ocr_confidence, 0.50)
        self.assertEqual(bill.ref, original_ref)
        self.assertEqual(bill.invoice_date, original_date)
        self.assertEqual(len(bill.invoice_line_ids), 1)

    @patch("odoo.addons.account_ocr_local.models.account_move.requests.post")
    def test_local_ocr_missing_confidence_creates_amount_line_without_header_overwrite(self, post):
        post.return_value = self._ocr_response(confidence=None, line_items=[])
        bill = self._bill()
        bill.journal_id.default_account_id = self.expense_account
        attachment = self._attachment(bill)
        original_ref = bill.ref
        original_date = bill.invoice_date

        bill._run_local_ocr(attachment, "http://127.0.0.1:8099")

        self.assertEqual(bill.local_ocr_state, "review")
        self.assertEqual(bill.local_ocr_confidence, 0.0)
        self.assertEqual(bill.ref, original_ref)
        self.assertEqual(bill.invoice_date, original_date)
        self.assertEqual(len(bill.invoice_line_ids), 2)
        ocr_line = bill.invoice_line_ids.filtered(lambda line: line.name == "OCR Vendor")
        self.assertEqual(ocr_line.price_unit, 120.0)
        self.assertFalse(ocr_line.product_id)
        self.assertFalse(ocr_line.tax_ids)

    @patch("odoo.addons.account_ocr_local.models.account_move.requests.post")
    def test_local_ocr_missing_confidence_uses_raw_grv_date_and_contact_ref(self, post):
        raw_text = (
            "GOLD MINTS PRODUCTS CO., LTD. Voucher No./talfi : GRV26-00431_\n"
            "Transaction Date/iuir' : L4/01./2026\n"
            "Customer/qnxd: 10300:lilliu6i1ui1lioiliuli1q\"dail\n"
            "Total 6402.0C 6,402.0C"
        )
        response = self._ocr_response(confidence=None, line_items=[], raw_text=raw_text)
        response.json.return_value["parsed_data"]["vendor_name"] = "?"
        response.json.return_value["parsed_data"]["tax_id"] = ""
        response.json.return_value["parsed_data"]["invoice_date"] = "2069-01-04"
        response.json.return_value["parsed_data"]["invoice_number"] = "/talfi"
        response.json.return_value["parsed_data"]["subtotal"] = 0.0
        response.json.return_value["parsed_data"]["total_amount"] = 0.0
        post.return_value = response
        bill = self._bill()
        bill.journal_id.default_account_id = self.expense_account
        attachment = self._attachment(bill)

        bill._run_local_ocr(attachment, "http://127.0.0.1:8099")

        self.assertEqual(bill.partner_id, self.customer_by_ref)
        self.assertEqual(bill.invoice_date, date(2026, 1, 14))
        self.assertEqual(bill.date, date(2026, 1, 14))
        ocr_line = bill.invoice_line_ids.filtered(lambda line: line.name == "GRV26-00431")
        self.assertEqual(ocr_line.price_unit, 6402.0)
        self.assertFalse(ocr_line.tax_ids)

    @patch("odoo.addons.account_ocr_local.models.account_move.requests.post")
    def test_local_ocr_missing_line_items_uses_raw_description_to_match_product(self, post):
        post.return_value = self._ocr_response(
            confidence=None,
            line_items=[],
            raw_text="INVOICE\nDescription: OCR Product\nTotal: 120.00",
        )
        bill = self._bill()
        attachment = self._attachment(bill)

        bill._run_local_ocr(attachment, "http://127.0.0.1:8099")

        ocr_line = bill.invoice_line_ids.filtered(lambda line: line.product_id == self.product)
        self.assertEqual(ocr_line.name, "OCR Product")
        self.assertEqual(ocr_line.price_unit, 120.0)

    @patch("odoo.addons.account_ocr_local.models.account_move.requests.post")
    def test_local_ocr_missing_amount_uses_raw_total_for_review_line(self, post):
        response = self._ocr_response(
            confidence=None,
            line_items=[],
            raw_text="Voucher No./talfi : GRV26-00431_\nTotal 6402.0C 6,402.0C",
        )
        response.json.return_value["parsed_data"]["subtotal"] = 0.0
        response.json.return_value["parsed_data"]["total_amount"] = 0.0
        post.return_value = response
        bill = self._bill()
        bill.journal_id.default_account_id = self.expense_account
        attachment = self._attachment(bill)

        bill._run_local_ocr(attachment, "http://127.0.0.1:8099")

        ocr_line = bill.invoice_line_ids.filtered(lambda line: line.name == "GRV26-00431")
        self.assertEqual(ocr_line.price_unit, 6402.0)
        self.assertFalse(ocr_line.product_id)
        self.assertFalse(ocr_line.tax_ids)

    def test_local_ocr_ignores_unsupported_attachment_type(self):
        bill = self._bill()
        attachment = self._attachment(bill, mimetype="text/plain")

        result = bill._run_local_ocr(attachment, "http://127.0.0.1:8099")

        self.assertFalse(result)
        self.assertEqual(len(bill.invoice_line_ids), 1)
