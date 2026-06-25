import base64
import io
import logging

from PyPDF2 import PdfReader

from odoo import models

_logger = logging.getLogger(__name__)


class DocumentsDocument(models.Model):
    _inherit = "documents.document"

    def _get_is_multipage(self):
        self.ensure_one()
        if self.mimetype not in ("application/pdf", "application/pdf;base64"):
            return super()._get_is_multipage()
        try:
            stream = io.BytesIO(base64.b64decode(self.datas or b""))
            return len(PdfReader(stream, strict=False).pages) > 1
        except Exception:
            _logger.warning("Impossible to count pages in %r.", self.name, exc_info=True)
            return False
