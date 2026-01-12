from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.onchange('partner_id')
    def _onchange_partner_set_journal(self):
        for move in self:
            if move.move_type not in ('out_invoice', 'out_refund'):
                continue
            company = move.company_id
            partner = move.partner_id
            company_country = company.country_id
            partner_country = partner.country_id
            if partner_country and company_country and partner_country.id == company_country.id:
                journal = company.auto_local_journal_id
            elif partner_country:
                journal = company.auto_foreign_journal_id
            else:
                journal = False
            if journal:
                move.journal_id = journal
                _logger.info(
                    "Journal auto-select (UI): move=%s type=%s partner=%s partner_country=%s company_country=%s journal=%s",
                    move.display_name,
                    move.move_type,
                    partner.display_name if partner else None,
                    partner_country.code if partner_country else None,
                    company_country.code if company_country else None,
                    journal.display_name,
                )
            else:
                _logger.info(
                    "Journal auto-select (UI): move=%s type=%s partner=%s partner_country=%s company_country=%s journal=%s",
                    move.display_name,
                    move.move_type,
                    partner.display_name if partner else None,
                    partner_country.code if partner_country else None,
                    company_country.code if company_country else None,
                    None,
                )
