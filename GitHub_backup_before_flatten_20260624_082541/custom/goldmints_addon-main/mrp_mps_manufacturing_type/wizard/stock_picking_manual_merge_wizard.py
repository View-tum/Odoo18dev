from odoo import Command, _, fields, models
from odoo.exceptions import UserError


class StockPickingManualMergeWizard(models.TransientModel):
    _name = "stock.picking.manual.merge.wizard"
    _description = "Manual Merge Internal Transfers"

    picking_ids = fields.Many2many(
        "stock.picking",
        string="Internal Transfers",
        required=True,
    )
    target_picking_id = fields.Many2one(
        "stock.picking",
        string="Target Transfer",
        compute="_compute_target_picking_id",
    )
    manufacturing_type = fields.Selection(
        selection=[
            ("plastic", "Plastic"),
            ("pharma", "Pharma"),
            ("packaging", "Packaging"),
        ],
        string="Manufacturing Type",
        compute="_compute_manufacturing_type",
    )

    def _compute_target_picking_id(self):
        for wizard in self:
            wizard.target_picking_id = wizard.picking_ids.sorted("id")[:1]

    def _compute_manufacturing_type(self):
        for wizard in self:
            manufacturing_types = wizard.picking_ids.mapped("manufacturing_type")
            wizard.manufacturing_type = manufacturing_types[0] if len(set(manufacturing_types)) == 1 else False

    def action_merge(self):
        self.ensure_one()
        pickings = self.picking_ids.exists().sorted("id")
        self._validate_pickings(pickings)
        target = pickings[:1]
        sources = pickings - target

        if not target.manufacturing_type:
            target.manufacturing_type = sources.filtered("manufacturing_type")[:1].manufacturing_type

        source_moves = sources.move_ids.filtered(lambda move: move.state != "cancel")
        if source_moves:
            source_moves.write({"picking_id": target.id})

        origins = list(dict.fromkeys((pickings.mapped("origin") or []) + pickings.mapped("name")))
        target.write({"origin": ", ".join(filter(None, origins))})

        if target.state == "draft":
            target.action_confirm()

        self._link_transfer_moves_to_mo_raw_moves(pickings)
        target.move_ids.filtered(lambda move: move.state not in ("done", "cancel", "draft"))._merge_moves()

        sources.write({"state": "cancel"})

        return {
            "type": "ir.actions.act_window",
            "res_model": "stock.picking",
            "res_id": target.id,
            "view_mode": "form",
            "target": "current",
        }

    def _validate_pickings(self, pickings):
        if len(pickings) < 2:
            raise UserError(_("Select at least two internal transfers to merge."))
        if any(picking.state in ("done", "cancel") for picking in pickings):
            raise UserError(_("Done or cancelled transfers cannot be merged."))
        if any(picking.picking_type_id.code != "internal" for picking in pickings):
            raise UserError(_("Only internal transfers can be merged."))
        self._validate_same_value(pickings, "company_id", _("Company"))
        self._validate_same_value(pickings, "picking_type_id", _("Operation Type"))
        self._validate_same_value(pickings, "location_id", _("Source Location"))
        self._validate_same_value(pickings, "location_dest_id", _("Destination Location"))
        self._validate_same_manufacturing_type(pickings)

    def _validate_same_value(self, pickings, field_name, label):
        values = pickings.mapped(field_name)
        if len(values) > 1:
            raise UserError(_("%s must be the same for all selected transfers.") % label)

    def _validate_same_manufacturing_type(self, pickings):
        manufacturing_types = set(filter(None, pickings.mapped("manufacturing_type")))
        if len(manufacturing_types) > 1:
            raise UserError(_("Manufacturing Type must be the same for all selected transfers."))

    def _link_transfer_moves_to_mo_raw_moves(self, pickings):
        for picking in pickings:
            productions = picking.production_ids.filtered(lambda production: production.state != "cancel")
            if not productions:
                continue
            for move in picking.move_ids.filtered(lambda item: item.state not in ("done", "cancel")):
                raw_moves = productions.move_raw_ids.filtered(
                    lambda raw: raw.state != "cancel"
                    and raw.product_id == move.product_id
                    and raw.product_uom == move.product_uom
                )
                if raw_moves:
                    move.write({"move_dest_ids": [Command.link(raw.id) for raw in raw_moves]})
