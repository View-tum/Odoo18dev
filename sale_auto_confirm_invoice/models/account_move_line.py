from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.model_create_multi
    def create(self, vals_list):
        today = fields.Date.context_today(self)
        for vals in vals_list:
            account_id = vals.get("account_id")
            if not account_id:
                continue
            account = self.env["account.account"].browse(account_id)
            date_maturity = vals.get("date_maturity")
            if account.account_type in ("asset_receivable", "liability_payable"):
                if not date_maturity:
                    vals["date_maturity"] = (
                        vals.get("invoice_date_due")
                        or vals.get("date")
                        or vals.get("invoice_date")
                        or today
                    )
            elif date_maturity:
                vals["date_maturity"] = False
        return super().create(vals_list)

    def write(self, vals):
        # Enforce date_maturity coherence when account_id/date_maturity change
        needs_check = {"account_id", "date_maturity"} & set(vals.keys())
        res = super().write(vals)
        if not needs_check:
            return res
        today = fields.Date.context_today(self)
        for line in self:
            account = line.account_id
            if account.account_type in ("asset_receivable", "liability_payable"):
                if not line.date_maturity:
                    line.date_maturity = line.move_id.invoice_date_due or line.move_id.date or today
            else:
                if line.date_maturity:
                    line.date_maturity = False
        return res

    @api.constrains("account_id", "date_maturity")
    def _check_date_maturity(self):
        today = fields.Date.context_today(self)
        for line in self:
            account_type = line.account_id.account_type
            if account_type in ("asset_receivable", "liability_payable"):
                if not line.date_maturity:
                    line.date_maturity = line.move_id.invoice_date_due or line.move_id.date or today
            else:
                if line.date_maturity:
                    line.date_maturity = False
        # Do not raise: we normalize instead
        return True
