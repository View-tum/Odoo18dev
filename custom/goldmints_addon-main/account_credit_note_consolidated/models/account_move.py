from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = "account.move"

    return_picking_ids = fields.Many2many(
        "stock.picking",
        "account_move_return_picking_rel",
        "move_id",
        "picking_id",
        string="Return Pickings",
        copy=False,
        check_company=True,
    )
    return_picking_count = fields.Integer(
        string="Return Count",
        compute="_compute_return_picking_count",
    )

    @api.depends("return_picking_ids")
    def _compute_return_picking_count(self):
        for move in self:
            move.return_picking_count = len(move.return_picking_ids)

    def write(self, vals):
        sync_keys = {"return_picking_ids", "state", "move_type"}
        sync_pickings = self.mapped("return_picking_ids") if sync_keys.intersection(vals) else self.env["stock.picking"]
        result = super().write(vals)
        if sync_keys.intersection(vals):
            sync_pickings |= self.mapped("return_picking_ids")
            sync_pickings.invalidate_recordset([
                "vendor_credit_note_ids",
                "vendor_credit_note_count",
                "vendor_credit_note_state",
            ])
        return result

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

    def action_view_return_pickings(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_picking_tree_all")
        action["domain"] = [("id", "in", self.return_picking_ids.ids)]
        if len(self.return_picking_ids) == 1:
            action.update({
                "view_mode": "form",
                "views": [(False, "form")],
                "res_id": self.return_picking_ids.id,
            })
        return action


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    return_picking_id = fields.Many2one(
        "stock.picking",
        string="Return Picking",
        copy=False,
        index=True,
        check_company=True,
    )
    return_stock_move_id = fields.Many2one(
        "stock.move",
        string="Return Stock Move",
        copy=False,
        index=True,
        check_company=True,
    )
