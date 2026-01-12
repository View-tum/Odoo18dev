from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    deferred_journal_id = fields.Many2one(
        "account.journal",
        string="Deferred Journal",
        domain="[('type', '=', 'general'), ('company_id', '=', company_id)]",
        copy=False,
    )
    deferred_account_id = fields.Many2one(
        "account.account",
        string="Deferred Account",
        domain="[('deprecated', '=', False), ('company_ids', 'parent_of', company_id)]",
        copy=False,
    )

    @api.onchange("product_id")
    def _onchange_deferred_defaults(self):
        for line in self:
            move = line.move_id
            if not move or not line.product_id:
                continue
            if move.is_purchase_document(include_receipts=True):
                j = line.product_id.product_tmpl_id.property_deferred_expense_journal_id or move.deferred_default_journal_id
                a = line.product_id.product_tmpl_id.property_deferred_expense_account_id or move.deferred_default_account_id
            else:
                j = line.product_id.product_tmpl_id.property_deferred_revenue_journal_id or move.deferred_default_journal_id
                a = line.product_id.product_tmpl_id.property_deferred_revenue_account_id or move.deferred_default_account_id
            if j and not line.deferred_journal_id:
                line.deferred_journal_id = j
            if a and not line.deferred_account_id:
                line.deferred_account_id = a

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            move_id = vals.get("move_id")
            product_id = vals.get("product_id")
            if move_id and product_id and (not vals.get("deferred_journal_id") or not vals.get("deferred_account_id")):
                move = self.env["account.move"].browse(move_id)
                product = self.env["product.product"].browse(product_id)
                if move.is_purchase_document(include_receipts=True):
                    j = product.product_tmpl_id.property_deferred_expense_journal_id or move.deferred_default_journal_id
                    a = product.product_tmpl_id.property_deferred_expense_account_id or move.deferred_default_account_id
                else:
                    j = product.product_tmpl_id.property_deferred_revenue_journal_id or move.deferred_default_journal_id
                    a = product.product_tmpl_id.property_deferred_revenue_account_id or move.deferred_default_account_id
                if j and not vals.get("deferred_journal_id"):
                    vals["deferred_journal_id"] = j.id
                if a and not vals.get("deferred_account_id"):
                    vals["deferred_account_id"] = a.id
        return super().create(vals_list)
