from odoo import api, fields, models, _


class StockPicking(models.Model):
    _inherit = "stock.picking"

    vendor_credit_note_ids = fields.Many2many(
        "account.move",
        string="Vendor Credit Notes",
        compute="_compute_vendor_credit_notes",
    )
    vendor_credit_note_count = fields.Integer(
        string="Vendor Credit Note Count",
        compute="_compute_vendor_credit_notes",
    )
    vendor_credit_note_state = fields.Selection(
        [
            ("not_required", "Not Required"),
            ("to_credit", "To Credit Note"),
            ("draft", "Draft Credit Note"),
            ("posted", "Credit Note Issued"),
            ("cancelled", "Credit Note Cancelled"),
        ],
        string="Vendor Credit Note Status",
        compute="_compute_vendor_credit_notes",
    )

    def _is_vendor_return_credit_note_candidate(self):
        self.ensure_one()
        return bool(
            self.state == "done"
            and self.return_id
            and self.partner_id
            and self.picking_type_id.code == "outgoing"
            and self.move_ids.filtered(lambda move: move.origin_returned_move_id and move.state == "done")
        )

    @api.depends("state", "return_id", "partner_id", "picking_type_id", "move_ids.origin_returned_move_id", "move_ids.state")
    def _compute_vendor_credit_notes(self):
        move_by_picking = {picking.id: self.env["account.move"] for picking in self}
        if self.ids:
            credit_notes = self.env["account.move"].search([
                ("move_type", "=", "in_refund"),
                ("return_picking_ids", "in", self.ids),
            ])
            for credit_note in credit_notes:
                for picking in credit_note.return_picking_ids.filtered(lambda item: item.id in move_by_picking):
                    move_by_picking[picking.id] |= credit_note

        for picking in self:
            credit_notes = move_by_picking.get(picking.id, self.env["account.move"])
            active_credit_notes = credit_notes.filtered(lambda move: move.state != "cancel")
            picking.vendor_credit_note_ids = credit_notes
            picking.vendor_credit_note_count = len(credit_notes)
            if not picking._is_vendor_return_credit_note_candidate():
                picking.vendor_credit_note_state = "not_required"
            elif not active_credit_notes:
                picking.vendor_credit_note_state = "to_credit"
            elif active_credit_notes.filtered(lambda move: move.state == "posted"):
                picking.vendor_credit_note_state = "posted"
            elif active_credit_notes.filtered(lambda move: move.state == "draft"):
                picking.vendor_credit_note_state = "draft"
            else:
                picking.vendor_credit_note_state = "cancelled"

    def action_view_vendor_credit_notes(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_in_refund_type")
        action["domain"] = [("id", "in", self.vendor_credit_note_ids.ids)]
        action["context"] = {"default_move_type": "in_refund", "move_type": "in_refund"}
        if len(self.vendor_credit_note_ids) == 1:
            action.update({
                "view_mode": "form",
                "views": [(False, "form")],
                "res_id": self.vendor_credit_note_ids.id,
            })
        return action
