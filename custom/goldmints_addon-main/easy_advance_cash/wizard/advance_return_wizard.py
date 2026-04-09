from odoo import api, fields, models


class AdvanceReturnWizard(models.TransientModel):
    _name = "advance.return.wizard"
    _description = "Clear Outstanding Balance"

    employee_id = fields.Many2one("hr.employee", string="Employee", required=True)
    balance = fields.Float(string="Outstanding", readonly=True)
    amount = fields.Float(string="Return Amount", required=True)
    journal_id = fields.Many2one(
        "account.journal",
        string="Journal",
        domain=[("type", "in", ["cash", "bank"])],
        required=True,
    )

    @api.onchange("employee_id")
    def _onchange_employee_id(self):
        if self.employee_id:
            # Calculate balance from logs
            logs = self.env["advance.cash.log"].search(
                [("employee_id", "=", self.employee_id.id), ("state", "=", "posted")]
            )
            # Payout(+), Expense(-), Return(-) -> amount_signed
            self.balance = sum(logs.mapped("amount_signed"))
            self.amount = self.balance

    def action_confirm(self):
        self.ensure_one()
        # Create Return Log
        # Logic: Payout=Pos, Return=Neg. So creating a 'Return' type with positive amount decreases balance.

        log = self.env["advance.cash.log"].create(
            {
                "date": fields.Date.today(),
                "transaction_type": "return",
                "employee_id": self.employee_id.id,
                "amount": self.amount,
                "journal_id": self.journal_id.id,
                "description": "Clear Outstanding",
                "state": "draft",
            }
        )
        log.action_confirm()

        return {
            "type": "ir.actions.act_window",
            "res_model": "advance.cash.log",
            "view_mode": "form",
            "res_id": log.id,
            "target": "current",
        }
