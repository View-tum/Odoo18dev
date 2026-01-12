# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from num2words import num2words
# from num_thai.thainumbers import NumThai
from odoo.exceptions import UserError


class dynamic_cheque_template(models.AbstractModel):
    _name = 'report.cheque_management.report_dynamic_check_print'
    
    def get_amount_in_word_line(self, payment_id, cheque_format):
        amount_word = payment_id.currency_id.with_context({"lang": "th_TH"}).amount_to_text(payment_id.amount)
        amount_word = amount_word.replace("and", "")
        amount_word = amount_word.replace(" ", "")
        amount_word = amount_word.replace("Baht", "บาท")
        amount_word = amount_word.replace("Satang", "สตางค์")
        amount_word = amount_word.replace("And", "")
        amount_word = amount_word.replace("และ", "")

        if payment_id.amount % 1 == 0.0:
            amount_word = amount_word + 'ถ้วน'

        first_line = (amount_word[0:cheque_format.words_in_fl_line])
        s1 = cheque_format.words_in_fl_line
        s2 = cheque_format.words_in_fl_line + cheque_format.words_in_sc_line
        second_line = (amount_word[s1:s2])
        localdict = {
            'first_line': first_line and first_line ,
            'second_line': second_line
        }
        return localdict

    def _get_report_values(self, docids, data=None):
        wizard = self.env['cheque.inbound.outbound'].browse(docids)
        if len(wizard.mapped('bank_account_journal_id')) > 1:
            raise UserError(_("You can't select different Bank Account!"))
        return {
            'doc_model': 'dynamic.cheque',
            'cheque_format': wizard.dynamic_io_cheque_id,
            'docs': wizard,
            'get_amount_in_word_line': self.get_amount_in_word_line,
        }


class report_paperformat(models.Model):
    _inherit = "report.paperformat"

    custom_report = fields.Boolean('Temp Formats', default=False)
