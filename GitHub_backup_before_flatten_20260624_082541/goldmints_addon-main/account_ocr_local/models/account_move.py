import logging
import re
from datetime import date, datetime

import requests
from PyPDF2.errors import DeprecationError

from odoo import Command, fields, models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    local_ocr_state = fields.Selection(
        [
            ("not_requested", "Not Requested"),
            ("processing", "Processing"),
            ("review", "Needs Review"),
            ("done", "Done"),
            ("error", "Error"),
            ("skipped", "Skipped"),
        ],
        string="Local OCR Status",
        default="not_requested",
        copy=False,
        tracking=True,
    )
    local_ocr_confidence = fields.Float(string="Local OCR Confidence", copy=False)
    local_ocr_document_type = fields.Selection(
        [
            ("file", "File"),
            ("handwritten", "Handwritten"),
            ("unknown", "Unknown"),
        ],
        string="Local OCR Document Type",
        copy=False,
    )
    local_ocr_raw_text = fields.Text(string="Local OCR Raw Text", copy=False)
    local_ocr_error = fields.Text(string="Local OCR Error", copy=False)
    local_ocr_attachment_id = fields.Many2one("ir.attachment", string="Local OCR Attachment", copy=False)

    def _local_ocr_param_bool(self, key, default=False):
        value = self.env["ir.config_parameter"].sudo().get_param(key)
        if value in (None, False):
            return default
        return str(value).strip().lower() in ("1", "true", "yes", "y", "on")

    def _local_ocr_param_float(self, key, default=0.0):
        value = self.env["ir.config_parameter"].sudo().get_param(key)
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _local_ocr_param_int(self, key, default=30):
        value = self.env["ir.config_parameter"].sudo().get_param(key)
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _local_ocr_enabled(self):
        return self._local_ocr_param_bool("account_ocr_local.local_ocr_enabled")

    def _get_ocr_option_can_extract(self):
        self.ensure_one()
        if self._local_ocr_enabled():
            return False
        return super()._get_ocr_option_can_extract()

    def _needs_auto_extract(self, new_document=False):
        self.ensure_one()
        if self._local_ocr_enabled():
            return False
        return super()._needs_auto_extract(new_document=new_document)

    def _extend_with_attachments(self, attachments, new=False):
        try:
            res = super()._extend_with_attachments(attachments, new=new)
        except DeprecationError as error:
            if not attachments.filtered(lambda attachment: attachment.mimetype == "application/pdf"):
                raise
            _logger.warning("Skipping standard PDF EDI unwrap because PyPDF2 is incompatible: %s", error)
            res = self.env["ir.attachment"]
        if not self._local_ocr_enabled():
            return res
        ocr_url = self.env["ir.config_parameter"].sudo().get_param(
            "account_ocr_local.local_ocr_server_url"
        ) or "http://127.0.0.1:8099"
        timeout = self._local_ocr_param_int("account_ocr_local.local_ocr_timeout", 30)
        for move in self.filtered(lambda m: m.move_type in ("in_invoice", "in_refund", "out_invoice", "out_refund")):
            for attachment in attachments:
                try:
                    move._run_local_ocr(attachment, ocr_url, timeout=timeout)
                except Exception:
                    _logger.exception("Local OCR failed for move %s attachment %s", move.display_name, attachment.display_name)
                    move.write({
                        "local_ocr_state": "error",
                        "local_ocr_error": "Unexpected local OCR error. Check server logs.",
                        "local_ocr_attachment_id": attachment.id,
                    })
        return res

    def _run_local_ocr(self, attachment, ocr_url, timeout=None):
        self.ensure_one()
        supported_mimetypes = {
            "application/pdf",
            "image/jpeg",
            "image/jpg",
            "image/png",
            "image/tiff",
            "image/bmp",
            "image/webp",
        }
        if attachment.mimetype not in supported_mimetypes:
            self.write({
                "local_ocr_state": "skipped",
                "local_ocr_error": "Unsupported attachment type.",
                "local_ocr_attachment_id": attachment.id,
            })
            return False
        file_content = attachment.raw
        if not file_content:
            self.write({
                "local_ocr_state": "error",
                "local_ocr_error": "Attachment has no content.",
                "local_ocr_attachment_id": attachment.id,
            })
            return False

        self.write({
            "local_ocr_state": "processing",
            "local_ocr_error": False,
            "local_ocr_attachment_id": attachment.id,
        })
        files = {"file": (attachment.name, file_content, attachment.mimetype)}
        try:
            response = requests.post(f"{ocr_url.rstrip('/')}/ocr", files=files, timeout=timeout or 30)
            response.raise_for_status()
            response_data = response.json()
        except requests.RequestException as error:
            self.write({
                "local_ocr_state": "error",
                "local_ocr_error": str(error),
            })
            return False
        except ValueError:
            self.write({
                "local_ocr_state": "error",
                "local_ocr_error": "Local OCR server returned invalid JSON.",
            })
            return False

        parsed = response_data.get("parsed_data") or {}
        if not parsed:
            self.write({
                "local_ocr_state": "review",
                "local_ocr_error": "Local OCR server returned no parsed data.",
                "local_ocr_raw_text": response_data.get("extracted_text"),
            })
            return False

        confidence_value = parsed.get("confidence", response_data.get("confidence"))
        has_confidence = confidence_value not in (None, False, "")
        confidence = self._local_ocr_to_float(confidence_value, 0.0)
        document_type = self._local_ocr_document_type(parsed)
        is_confident = confidence >= self._local_ocr_param_float(
            "account_ocr_local.local_ocr_confidence_threshold", 0.90
        )
        raw_text = response_data.get("extracted_text")
        can_create_lines = is_confident or (not has_confidence and self._local_ocr_has_amount(parsed, raw_text))
        values = {
            "local_ocr_state": "review",
            "local_ocr_confidence": confidence,
            "local_ocr_document_type": document_type,
            "local_ocr_raw_text": raw_text,
            "local_ocr_error": False,
        }
        if "extract_state" in self._fields:
            values["extract_state"] = "waiting_validation"

        if is_confident:
            partner = self._local_ocr_find_partner(parsed)
            if partner:
                values["partner_id"] = partner.id

            invoice_date = self._local_ocr_parse_date(parsed.get("invoice_date"))
            if invoice_date:
                values["invoice_date"] = invoice_date
                values["date"] = invoice_date

            invoice_number = parsed.get("invoice_number") or parsed.get("ref")
            if invoice_number:
                if self.move_type in ("in_invoice", "in_refund"):
                    values["ref"] = invoice_number
                else:
                    values["payment_reference"] = invoice_number

        if not is_confident and not has_confidence:
            fallback_partner = self._local_ocr_find_partner_from_raw(raw_text)
            if fallback_partner:
                values["partner_id"] = fallback_partner.id

            fallback_date = self._local_ocr_extract_transaction_date(raw_text)
            if fallback_date:
                values["invoice_date"] = fallback_date
                values["date"] = fallback_date

        if can_create_lines:
            line_commands = self._local_ocr_prepare_line_commands(parsed, raw_text)
            if line_commands:
                if self._local_ocr_param_bool("account_ocr_local.local_ocr_replace_lines"):
                    values["invoice_line_ids"] = [Command.clear()] + line_commands
                else:
                    values["invoice_line_ids"] = line_commands

        self.write(values)
        return True

    def _local_ocr_has_amount(self, parsed, raw_text=None):
        return self._local_ocr_amount(parsed, raw_text) > 0

    def _local_ocr_find_partner(self, parsed):
        partner = self.env["res.partner"]
        tax_id = (parsed.get("tax_id") or parsed.get("vat") or "").strip()
        if tax_id:
            partner = partner.search([("vat", "=", tax_id)], limit=1)
        if not partner:
            vendor_name = (parsed.get("vendor_name") or parsed.get("partner_name") or "").strip()
            if vendor_name:
                partner = self.env["res.partner"].search([("name", "ilike", vendor_name)], limit=1)
        return partner

    def _local_ocr_find_partner_from_raw(self, raw_text):
        partner_ref = self._local_ocr_extract_partner_ref(raw_text)
        if not partner_ref:
            return self.env["res.partner"]
        return self.env["res.partner"].search([("ref", "=", partner_ref)], limit=1)

    def _local_ocr_extract_partner_ref(self, raw_text):
        if not raw_text:
            return False
        patterns = (
            r"(?im)\bCustomer[^\n:]*:\s*([0-9]{3,})\s*:",
            r"(?im)\bCustomer\s+Code[^\n:]*:\s*([0-9]{3,})\b",
        )
        for pattern in patterns:
            match = re.search(pattern, raw_text)
            if match:
                return match.group(1)
        return False

    def _local_ocr_prepare_line_commands(self, parsed, raw_text=None):
        line_items = parsed.get("line_items") or []
        commands = []
        fallback_amount = self._local_ocr_amount(parsed, raw_text)
        if not line_items and fallback_amount > 0:
            voucher_number = self._local_ocr_extract_voucher_number(raw_text)
            fallback_description = (
                parsed.get("description")
                or parsed.get("product_name")
                or self._local_ocr_extract_text_value(raw_text, "description")
                or voucher_number
                or parsed.get("vendor_name")
                or parsed.get("invoice_number")
                or "OCR Document"
            )
            line_items = [{
                "description": fallback_description,
                "product_name": fallback_description,
                "quantity": 1.0,
                "price_unit": fallback_amount,
                "tax_ids": [],
            }]
        for item in line_items:
            command = self._local_ocr_prepare_line_command(item)
            if command:
                commands.append(command)
        return commands

    def _local_ocr_extract_text_value(self, raw_text, label):
        if not raw_text:
            return False
        pattern = rf"(?im)^\s*{re.escape(label)}\s*:\s*(.+?)\s*$"
        match = re.search(pattern, raw_text)
        return match.group(1).strip() if match else False

    def _local_ocr_amount(self, parsed, raw_text=None):
        amount_keys = ("subtotal", "untaxed_amount", "amount", "total_amount", "total")
        for key in amount_keys:
            amount = self._local_ocr_to_float(parsed.get(key), 0.0)
            if amount > 0:
                return amount
        return self._local_ocr_extract_total_amount(raw_text)

    def _local_ocr_extract_total_amount(self, raw_text):
        if not raw_text:
            return 0.0
        patterns = (
            r"(?im)^\s*Total\s+([0-9][0-9,]*(?:\.[0-9OC]{1,2})?)(?:\s+([0-9][0-9,]*(?:\.[0-9OC]{1,2})?))?",
            r"(?im)^\s*Total\s+Amount[^\n0-9]*([0-9][0-9,]*(?:\.[0-9OC]{1,2})?)",
        )
        for pattern in patterns:
            for match in re.finditer(pattern, raw_text):
                value = match.group(2) or match.group(1)
                amount = self._local_ocr_to_float(self._local_ocr_normalize_amount_text(value), 0.0)
                if amount > 0:
                    return amount
        return 0.0

    def _local_ocr_extract_voucher_number(self, raw_text):
        if not raw_text:
            return False
        match = re.search(r"(?im)\bVoucher\s+No\.[^:]*:\s*([A-Z0-9/_-]+)", raw_text)
        return match.group(1).strip("_ /") if match else False

    def _local_ocr_normalize_amount_text(self, value):
        return str(value or "").upper().replace("O", "0").replace("C", "0")

    def _local_ocr_extract_transaction_date(self, raw_text):
        if not raw_text:
            return False
        labels = ("Transaction Date", "Document Date", "Invoice Date", "Date")
        for label in labels:
            pattern = rf"(?im)\b{re.escape(label)}[^\n:]*:\s*([A-Z0-9./-]+)"
            match = re.search(pattern, raw_text)
            if not match:
                continue
            parsed_date = self._local_ocr_parse_date(self._local_ocr_normalize_date_text(match.group(1)))
            if parsed_date and self._local_ocr_is_reasonable_date(parsed_date):
                return parsed_date
        return False

    def _local_ocr_normalize_date_text(self, value):
        text = str(value or "").strip().upper()
        text = text.replace("L", "1").replace("I", "1").replace("O", "0")
        return re.sub(r"[^0-9/-]", "", text)

    def _local_ocr_is_reasonable_date(self, value):
        today = fields.Date.context_today(self)
        return 2000 <= value.year <= today.year + 1

    def _local_ocr_prepare_line_command(self, item):
        product = self._local_ocr_find_product(item)
        account = self._local_ocr_line_account(product)
        if not account:
            return False
        quantity = self._local_ocr_to_float(item.get("quantity") or item.get("qty"), 1.0) or 1.0
        price_unit = self._local_ocr_to_float(item.get("price_unit"), None)
        if price_unit is None:
            amount = self._local_ocr_to_float(item.get("subtotal") or item.get("amount") or item.get("total"), 0.0)
            price_unit = amount / quantity if quantity else amount
        tax_ids = item.get("tax_ids")
        if tax_ids is None:
            tax_ids = self._local_ocr_line_taxes(product).ids
        line_values = {
            "name": item.get("description") or item.get("product_name") or "OCR Document",
            "quantity": quantity,
            "price_unit": price_unit,
            "account_id": account.id,
            "tax_ids": [Command.set(tax_ids)],
        }
        if product:
            line_values["product_id"] = product.id
        return Command.create(line_values)

    def _local_ocr_find_product(self, item):
        product_model = self.env["product.product"]
        code = (item.get("product_code") or item.get("default_code") or item.get("barcode") or "").strip()
        if code:
            product = product_model.search(["|", ("default_code", "=", code), ("barcode", "=", code)], limit=1)
            if product:
                return product
        name = (item.get("product_name") or item.get("description") or "").strip()
        if name:
            return product_model.search([("name", "ilike", name)], limit=1)
        return product_model

    def _local_ocr_line_account(self, product):
        is_sale = self.is_sale_document(include_receipts=True)
        if product:
            accounts = product.with_company(self.company_id).product_tmpl_id.get_product_accounts(
                fiscal_pos=self.fiscal_position_id
            )
            account = accounts["income"] if is_sale else accounts["expense"]
            if account:
                return account
        fallback_account = self.journal_id.default_account_id
        if fallback_account and fallback_account.account_type not in (
            "asset_receivable",
            "liability_payable",
            "asset_cash",
            "liability_credit_card",
            "off_balance",
        ):
            return fallback_account
        return self.env["account.account"]

    def _local_ocr_line_taxes(self, product):
        is_sale = self.is_sale_document(include_receipts=True)
        tax_type = "sale" if is_sale else "purchase"
        taxes = self.env["account.tax"]
        if product:
            taxes = product.taxes_id if is_sale else product.supplier_taxes_id
            taxes = taxes.filtered(lambda tax: tax.company_id == self.company_id and tax.type_tax_use == tax_type)
        if not taxes:
            taxes = self.company_id.account_sale_tax_id if is_sale else self.company_id.account_purchase_tax_id
        if self.fiscal_position_id:
            taxes = self.fiscal_position_id.map_tax(taxes)
        return taxes

    def _local_ocr_document_type(self, parsed):
        value = (parsed.get("document_type") or parsed.get("source_type") or "").strip().lower()
        if value in ("handwritten", "handwrite", "handwriting", "manual"):
            return "handwritten"
        if value in ("file", "printed", "digital", "pdf", "scan", "scanned"):
            return "file"
        return "unknown"

    def _local_ocr_parse_date(self, value):
        if not value:
            return False
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        text_value = str(value).strip()
        parsed_date = self._local_ocr_parse_numeric_date(text_value)
        if parsed_date:
            return parsed_date
        try:
            return fields.Date.to_date(text_value)
        except (TypeError, ValueError):
            return False

    def _local_ocr_parse_numeric_date(self, value):
        separator = "-" if "-" in value else "/" if "/" in value else False
        if not separator:
            return False
        parts = value.split(separator)
        if len(parts) != 3 or not all(part.isdigit() for part in parts):
            return False
        numbers = [int(part) for part in parts]
        if len(parts[0]) == 4:
            year, month, day = numbers
        elif numbers[0] > 12:
            day, month, year = numbers
        elif numbers[1] > 12:
            month, day, year = numbers
        else:
            day, month, year = numbers
        try:
            return date(year, month, day)
        except ValueError:
            return False

    def _local_ocr_to_float(self, value, default=0.0):
        if value in (None, False, ""):
            return default
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(str(value).replace(",", "").strip())
        except (TypeError, ValueError):
            return default
