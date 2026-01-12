# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    type = fields.Selection(
        selection_add=[("opening", "Opening/Closing Situation")],
        ondelete={"opening": "cascade"},
    )

    payment_debit_account_id = fields.Many2one("account.account")
    payment_credit_account_id = fields.Many2one("account.account")
