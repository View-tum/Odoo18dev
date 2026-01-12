from odoo import models
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()
        partner = self.partner_invoice_id or self.partner_id
        company = self.company_id
        company_country = company.country_id
        partner_country = partner.country_id if partner else False
        journal = False
        if partner_country and company_country and partner_country.id == company_country.id:
            journal = company.auto_local_journal_id
        elif partner_country:
            journal = company.auto_foreign_journal_id
        if journal:
            invoice_vals['journal_id'] = journal.id
            _logger.info(
                "Journal auto-select (SO->INV): order=%s partner=%s partner_country=%s company_country=%s journal=%s",
                self.name,
                partner.display_name if partner else None,
                partner_country.code if partner_country else None,
                company_country.code if company_country else None,
                journal.display_name,
            )
        else:
            _logger.info(
                "Journal auto-select (SO->INV): order=%s partner=%s partner_country=%s company_country=%s journal=%s",
                self.name,
                partner.display_name if partner else None,
                partner_country.code if partner_country else None,
                company_country.code if company_country else None,
                None,
            )
        return invoice_vals
