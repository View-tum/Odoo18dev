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

    def _ocr_response(self, confidence=0.98, line_items=None):
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "extracted_text": "OCR text",
            "parsed_data": {
                "vendor_name": "OCR Vendor",
                "tax_id": "0105559999999",
                "invoice_date": str(fields.Date.today()),
                "invoice_number": "OCR-INV-001",
                "subtotal": 120.0,
                "vat_amount": 0.0,
                "total_amount": 120.0,
                "confidence": confidence,
                "document_type": "handwritten",
                "line_items": line_items or [{
                    "description": "OCR Product",
                    "quantity": 2.0,
                    "price_unit": 60.0,
                    "product_code": self.product.default_code or "",
                    "product_name": self.product.name,
                }],
            },
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

    def test_local_ocr_ignores_unsupported_attachment_type(self):
        bill = self._bill()
        attachment = self._attachment(bill, mimetype="text/plain")

        result = bill._run_local_ocr(attachment, "http://127.0.0.1:8099")

        self.assertFalse(result)
        self.assertEqual(len(bill.invoice_line_ids), 1)
