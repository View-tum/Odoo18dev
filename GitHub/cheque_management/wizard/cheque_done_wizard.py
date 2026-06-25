from odoo import api, fields, models
from odoo.exceptions import UserError


class ChequeDoneWizard(models.TransientModel):
    _name = "cheque.done.wizard"
    _description = "Done Cheques Wizard"

    payment_date = fields.Date(
        string="Payment Date",
        required=True,
        default=fields.Date.context_today,
    )
    line_ids = fields.One2many(
        "cheque.done.wizard.line",
        "wizard_id",
        string="Cheques",
    )

    def action_confirm(self):
        self.ensure_one()
        if not self.payment_date:
            raise UserError("กรุณากรอก Payment Date ก่อน Confirm")
        for line in self.line_ids:
            cheque = line.cheque_id
            cheque.date = self.payment_date
            if cheque.state in ('draft', 'waiting_confirm'):
                cheque.action_confirm_pay()
            if cheque.state == 'confirmed':
                cheque.action_bank_deposit()
            if cheque.state == 'bank_deposit':
                cheque.action_validate()
        return {'type': 'ir.actions.act_window_close'}


class ChequeDoneWizardLine(models.TransientModel):
    _name = "cheque.done.wizard.line"
    _description = "Done Cheques Wizard Line"

    wizard_id = fields.Many2one(
        "cheque.done.wizard",
        string="Wizard",
        ondelete="cascade",
    )
    cheque_id = fields.Many2one(
        "cheque.inbound.outbound",
        string="Cheque",
        readonly=True,
    )
    cheque_name = fields.Char(
        related="cheque_id.display_name",
        string="Cheque No.",
    )
    partner_name = fields.Char(
        related="cheque_id.pay_partner_id.name",
        string="Partner",
    )
    amount = fields.Monetary(
        related="cheque_id.amount",
        string="Amount",
    )
    currency_id = fields.Many2one(
        related="cheque_id.currency_id",
    )
    cheque_state = fields.Selection(
        related="cheque_id.state",
        string="Status",
    )
