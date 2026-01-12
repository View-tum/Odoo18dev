# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    mpc_market_scope = fields.Selection(
        selection=[
            ("domestic", "Domestic"),
            ("inter", "International"),
        ],
        compute="_compute_mpc_market_scope",
        store=True,
        string="Market Scope",
    )

    @api.depends(
        "procurement_group_id.sale_id",
        "origin",
        "sale_line_id.order_id",
        "move_finished_ids.move_dest_ids.raw_material_production_id.mpc_market_scope",
    )
    def _compute_mpc_market_scope(self):
        for mo in self:
            scope = False
            # 1. Direct Links (Standard MTO or linked SO)
            so = mo.procurement_group_id.sale_id or mo.sale_line_id.order_id
            if so:
                scope = so.so_type_id.market_scope

            # 2. Native Odoo Link (Traversal from Parent MO via Moves)
            if not scope:
                # Find MO that consumes this MO's output
                # move_dest_ids on the finished moves points to the next step
                parent_mo = (
                    mo.move_finished_ids.move_dest_ids.raw_material_production_id
                )
                if parent_mo:
                    # Take the scope from the parent MO (it handles its own parent if nested)
                    scope = parent_mo[:1].mpc_market_scope

            # 3. Origin Chain Link (Handle our create override or standard Odoo)
            if not scope and mo.origin:
                if not mo.origin.startswith("WH/MO/"):
                    # Fallback search for SO by name
                    sale = self.env["sale.order"].search(
                        [("name", "=", mo.origin)], limit=1
                    )
                    if sale:
                        scope = sale.so_type_id.market_scope
                else:
                    # Fallback search for Parent MO by name
                    parent_by_name = self.env["mrp.production"].search(
                        [("name", "=", mo.origin)], limit=1
                    )
                    if parent_by_name:
                        scope = parent_by_name.mpc_market_scope

            mo.mpc_market_scope = scope or "domestic"

    def _post_run_manufacture(self, procurements):
        res = super()._post_run_manufacture(procurements)
        for production in self:
            production._check_intl_notification()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            so_name = False
            # 1. Try to get SO from procurement group (strongest link for MTO chains)
            if vals.get("procurement_group_id"):
                group = self.env["procurement.group"].browse(
                    vals["procurement_group_id"]
                )
                if group.sale_id:
                    so_name = group.sale_id.name

            # 2. If origin is an MO, try to find the original SO from parent hierarchy
            if (
                not so_name
                and vals.get("origin")
                and vals["origin"].startswith("WH/MO/")
            ):
                parent_mo = self.env["mrp.production"].search(
                    [("name", "=", vals["origin"])], limit=1
                )
                if parent_mo:
                    # If parent already has an SO ref in its origin, take it
                    if parent_mo.origin and not parent_mo.origin.startswith("WH/MO/"):
                        so_name = parent_mo.origin
                    else:
                        # Check direct links on parent
                        so = (
                            parent_mo.sale_line_id.order_id
                            or parent_mo.procurement_group_id.sale_id
                        )
                        if so:
                            so_name = so.name

            if so_name:
                vals["origin"] = so_name

        return super().create(vals_list)

    def _check_intl_notification(self):
        self.ensure_one()

        so = self.sale_line_id.order_id or self.procurement_group_id.sale_id

        if (
            so
            and so.so_type_id.market_scope == "inter"
            and self.product_id.x_intl_notify
        ):
            self._create_intl_production_activity(so)

    def _create_intl_production_activity(self, so):
        self.ensure_one()
        activity_type = self.env.ref("mail.mail_activity_data_todo")

        # Target all users in the 'Production / Administrator' group
        group_mrp_manager = self.env.ref("mrp.group_mrp_manager")
        recipient_users = group_mrp_manager.users.filtered(lambda u: u.active)

        if not recipient_users:
            # Fallback to current user if group has no users (unlikely)
            recipient_users = self.env.user

        summary = _("IMPORTANT: International Order Production")
        note = _(
            "This Manufacturing Order is linked to International Sales Order <b>%s</b>. "
            "Please prioritize according to international shipping requirements.",
            so.name,
        )

        for user in recipient_users:
            self.activity_schedule(
                activity_type_id=activity_type.id,
                summary=summary,
                note=note,
                user_id=user.id,
                date_deadline=fields.Date.today(),
            )
