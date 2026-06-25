from odoo import fields, models


class ChequeInboundOutbound(models.Model):
    _inherit = "cheque.inbound.outbound"

    advance_cash_id = fields.Many2one(
        "advance.cash.log", string="Advance Cash", readonly=True, copy=False
    )

    def action_open_advance_cash(self):
        self.ensure_one()
        return {
            "name": "Advance Cash",
            "type": "ir.actions.act_window",
            "res_model": "advance.cash.log",
            "view_mode": "form",
            "res_id": self.advance_cash_id.id,
        }
