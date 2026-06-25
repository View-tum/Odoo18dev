from odoo import models, fields


class AccountMoveInherit(models.Model):
    """
    Extend account.move to track multi-bill reversal links.

    Standard Odoo reversed_entry_id (Many2one) supports only 1-to-1 reversal.
    consolidated_bill_ids tracks the full set of bills that a CN was built from,
    and consolidated_cn_id lets each original bill point back to its consolidated CN.
    """
    _inherit = 'account.move'

    # On the Credit Note: which bills were consolidated into this CN?
    consolidated_bill_ids = fields.Many2many(
        comodel_name='account.move',
        relation='account_move_multi_reversal_rel',
        column1='credit_note_id',
        column2='bill_id',
        string='Reversed Bills',
        copy=False,
        readonly=True,
        help='Vendor Bills that were reversed into this consolidated Credit Note.',
    )

    # On each Bill: which consolidated CN was created from this bill?
    consolidated_cn_id = fields.Many2one(
        comodel_name='account.move',
        string='Consolidated Credit Note',
        copy=False,
        readonly=True,
        ondelete='set null',
        help='The consolidated Credit Note created from this Vendor Bill.',
    )

    # Customer reference — replaces the ref-as-Customer-Reference slot on CNs
    customer_ref = fields.Char(
        string='Customer Reference',
        copy=False,
    )

