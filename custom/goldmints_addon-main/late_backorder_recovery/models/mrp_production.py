# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    late_backorder_source_id = fields.Many2one(
        "mrp.production",
        string="Late Backorder Source MO",
        copy=False,
        index=True,
    )
    late_backorder_ids = fields.One2many(
        "mrp.production",
        "late_backorder_source_id",
        string="Late Backorders",
    )
    can_create_late_backorder = fields.Boolean(
        compute="_compute_late_backorder_state",
        string="Can Create Late Backorder",
    )
    late_backorder_remaining_qty = fields.Float(
        compute="_compute_late_backorder_state",
        string="Late Backorder Remaining Qty",
        digits="Product Unit of Measure",
    )

    def _get_late_backorder_rounding(self):
        self.ensure_one()
        rounding = (
            self.product_uom_id.rounding
            or self.product_id.uom_id.rounding
            or 0.01
        )
        return rounding if rounding > 0 else 0.01

    def _get_late_backorder_remaining_qty(self):
        self.ensure_one()
        remaining_qty = max(self.product_qty - self.qty_produced, 0.0)
        if float_compare(
            remaining_qty,
            0.0,
            precision_rounding=self._get_late_backorder_rounding(),
        ) <= 0:
            return 0.0
        return remaining_qty

    def _has_existing_standard_backorder(self):
        self.ensure_one()
        if not self.backorder_sequence or not self.procurement_group_id:
            return False
        siblings = self.procurement_group_id.mrp_production_ids.filtered(
            lambda mo: mo.id != self.id
            and mo.product_id == self.product_id
            and mo.bom_id == self.bom_id
            and mo.state != "cancel"
        )
        return bool(siblings)

    @api.depends(
        "state",
        "product_qty",
        "qty_produced",
        "late_backorder_ids",
        "procurement_group_id.mrp_production_ids.backorder_sequence",
        "procurement_group_id.mrp_production_ids.state",
    )
    def _compute_late_backorder_state(self):
        for production in self:
            remaining_qty = production._get_late_backorder_remaining_qty()
            eligible = (
                production.state == "done"
                and not production.late_backorder_ids
                and not production._has_existing_standard_backorder()
                and float_compare(
                    remaining_qty,
                    0.0,
                    precision_rounding=production._get_late_backorder_rounding(),
                )
                > 0
            )
            production.late_backorder_remaining_qty = remaining_qty
            production.can_create_late_backorder = eligible

    def action_create_late_backorder(self):
        self.ensure_one()
        if not self.can_create_late_backorder:
            raise UserError(
                _("This manufacturing order is not eligible for late backorder creation.")
            )

        remaining_qty = self._get_late_backorder_remaining_qty()
        if not remaining_qty:
            raise UserError(_("There is no remaining quantity to backorder."))

        if not self.procurement_group_id:
            self.procurement_group_id = self.env["procurement.group"].create(
                {"name": self.name}
            )

        next_seq = max(
            self.procurement_group_id.mrp_production_ids.mapped("backorder_sequence"),
            default=0,
        ) + 1
        
        # Odoo 18 doesn't have _get_name_backorder, handle it directly or safely
        backorder_name = f"{self.name}-{next_seq:03d}"
        if hasattr(self, '_get_name_backorder'):
            try:
                backorder_name = self._get_name_backorder(self.name, next_seq)
            except Exception:
                pass
                
        backorder_vals = {
            "name": backorder_name,
            "product_id": self.product_id.id,
            "product_qty": remaining_qty,
            "product_uom_id": self.product_uom_id.id,
            "bom_id": self.bom_id.id,
            "picking_type_id": self.picking_type_id.id,
            "location_src_id": self.location_src_id.id,
            "location_dest_id": self.location_dest_id.id,
            "company_id": self.company_id.id,
            "procurement_group_id": self.procurement_group_id.id,
            "origin": self.origin,
            "date_start": self.date_start,
            "date_deadline": self.date_deadline,
            "orderpoint_id": self.orderpoint_id.id,
            "priority": self.priority,
            "propagate_cancel": self.propagate_cancel,
            "backorder_sequence": next_seq,
            "late_backorder_source_id": self.id,
        }
        backorder = self.create(backorder_vals)
        backorder.action_confirm()

        self.message_post(
            body=_(
                "A late backorder %s has been created after the original manufacturing order was finished without backorder."
            )
            % backorder._get_html_link()
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "mrp.production",
            "res_id": backorder.id,
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "current",
        }
