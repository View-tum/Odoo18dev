from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    log_ids = fields.One2many("advance.cash.log", "employee_id", string="Advances")
    advance_balance = fields.Float(
        string="Advance Balance", compute="_compute_advance_balance", store=True
    )

    @api.depends(
        "log_ids.amount_signed", "log_ids.state", "log_ids.reimburse_move_id.state"
    )
    def _compute_advance_balance(self):
        for rec in self:
            logs = rec.log_ids.filtered(lambda log: log.state == "posted")
            balance = sum(logs.mapped("amount_signed"))

            advance_accounts = (
                self.env["account.journal"]
                .search([("advance_account_id", "!=", False)])
                .mapped("advance_account_id")
            )
            if self.env.company.advance_cash_reimbursement_account_id:
                advance_accounts += (
                    self.env.company.advance_cash_reimbursement_account_id
                )

            for log in logs:
                if log.reimburse_move_id and log.reimburse_move_id.state == "posted":
                    lines = log.reimburse_move_id.line_ids.filtered(
                        lambda l: l.account_id in advance_accounts
                    )
                    balance += sum(lines.mapped("debit")) - sum(lines.mapped("credit"))

            rec.advance_balance = balance

    def action_sync_balance(self):
        self.ensure_one()
        self._compute_advance_balance()
        return True

    def action_open_advance_logs(self):
        return {
            "name": "Advance Cash Logs",
            "type": "ir.actions.act_window",
            "res_model": "advance.cash.log",
            "view_mode": "list,form",
            "domain": [("employee_id", "=", self.id)],
            "context": {"default_employee_id": self.id},
        }
