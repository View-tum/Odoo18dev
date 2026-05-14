from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_open_consolidation_wizard(self):
        self.ensure_one()
        return {
            "name": _("Consolidate Bills and Returns"),
            "type": "ir.actions.act_window",
            "res_model": "account.move.consolidated.reversal",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_move_id": self.id,
                "default_partner_id": self.partner_id.id,
            },
        }
