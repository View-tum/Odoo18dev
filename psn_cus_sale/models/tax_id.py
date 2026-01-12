from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'
    _order = 'id desc'  # เรียงจาก id มากสุดไปน้อย

    @api.constrains('vat')
    def _check_tax_id(self):
        for partner in self:
            _logger.info(f"Checking VAT: {partner.vat}")
            if partner.vat:
                vat_clean = partner.vat.replace('-', '').replace(' ', '')
                if not vat_clean.isdigit():
                    raise ValidationError("เลขประจำตัวผู้เสียภาษีต้องเป็นตัวเลขเท่านั้น")
                if len(vat_clean) != 13:
                    raise ValidationError("เลขประจำตัวผู้เสียภาษีต้องมีความยาว 13 หลัก")
