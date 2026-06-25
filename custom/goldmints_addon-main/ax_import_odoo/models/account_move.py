# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    ax_voucher_number = fields.Char(
        string="AX Voucher No.",
        index=True,
        copy=False,
        readonly=True,
    )
    ax_voucher_type = fields.Char(
        string="AX Voucher Type",
        copy=False,
        readonly=True,
    )
    ax_document_number = fields.Char(
        string="AX Document No.",
        copy=False,
        readonly=True,
    )
    ax_journal_number = fields.Char(
        string="AX Journal No.",
        copy=False,
        readonly=True,
    )
    ax_journal_description = fields.Char(
        string="AX Journal Description",
        copy=False,
        readonly=True,
    )
    ax_source_filename = fields.Char(
        string="AX Source File",
        copy=False,
        readonly=True,
    )


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    ax_account_code = fields.Char(
        string="AX Account No.",
        copy=False,
        readonly=True,
    )
