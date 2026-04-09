from odoo import models, fields, api, _


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    manufacturing_type = fields.Selection(
        related="product_id.product_tmpl_id.manufacturing_type",
        store=True,
        readonly=True,
        string="Manufacturing Type",
    )

    mpc_market_scope = fields.Selection(
        selection=[
            ("domestic", "Domestic"),
            ("inter", "International"),
        ],
        compute="_compute_mpc_market_scope",
        store=True,
        string="Market Scope (Internal)",
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
                parent_mo = mo.move_finished_ids.move_dest_ids.raw_material_production_id
                if parent_mo:
                    scope = parent_mo[:1].mpc_market_scope

            # 3. Origin Chain Link
            if not scope and mo.origin:
                if not mo.origin.startswith("WH/MO/"):
                    sale = self.env["sale.order"].search([("name", "=", mo.origin)], limit=1)
                    if sale:
                        scope = sale.so_type_id.market_scope
                else:
                    parent_by_name = self.env["mrp.production"].search([("name", "=", mo.origin)], limit=1)
                    if parent_by_name:
                        scope = parent_by_name.mpc_market_scope

            mo.mpc_market_scope = scope or "domestic"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            so_name = False
            if vals.get("procurement_group_id"):
                group = self.env["procurement.group"].browse(vals["procurement_group_id"])
                if group.sale_id:
                    so_name = group.sale_id.name

            if not so_name and vals.get("origin") and vals["origin"].startswith("WH/MO/"):
                parent_mo = self.env["mrp.production"].search([("name", "=", vals["origin"])], limit=1)
                if parent_mo:
                    if parent_mo.origin and not parent_mo.origin.startswith("WH/MO/"):
                        so_name = parent_mo.origin
                    else:
                        so = parent_mo.sale_line_id.order_id or parent_mo.procurement_group_id.sale_id
                        if so:
                            so_name = so.name

            if so_name:
                vals["origin"] = so_name

        return super().create(vals_list)

    def _post_run_manufacture(self, procurements):
        res = super()._post_run_manufacture(procurements)
        for production in self:
            production._check_important_notification()
        return res

    def _check_important_notification(self):
        self.ensure_one()
        so = self.sale_line_id.order_id or self.procurement_group_id.sale_id
        if so and so.so_type_id.market_scope == "inter" and self.product_id.x_important_notify:
            self._send_important_popup_alert(so)

    def _send_important_popup_alert(self, so):
        self.ensure_one()
        # Determine factory-specific group
        factory_type = self.product_id.manufacturing_type
        if factory_type == "plastic":
            group_xml_id = "mrp_mps_manufacturing_type.group_mrp_manager_plastic"
        elif factory_type == "pharma":
            group_xml_id = "mrp_mps_manufacturing_type.group_mrp_manager_pharma"
        else:
            group_xml_id = "mrp_mps_manufacturing_type.group_mrp_manager_packaging"
        group = self.env.ref(group_xml_id, raise_if_not_found=False)
        notify_users = group.users.filtered(lambda u: u.active)

        if not notify_users:
            # Fallback to general MRP manager if specialized group is empty
            notify_users = self.env.ref("mrp.group_mrp_manager").users.filtered(lambda u: u.active)

        if not notify_users:
            notify_users = self.env.user

        title = _("IMPORTANT PRODUCTION ALERT")
        message = _("Manufacturing Order %s is linked to International Sales Order %s. Please prioritize immediately!") % (self.name, so.name)

        for user in notify_users:
            self.env["bus.bus"]._sendone(
                user.partner_id,
                "simple_notification",
                {
                    "type": "danger",
                    "title": title,
                    "message": message,
                    "sticky": True,
                },
            )

        # Also keep a light activity for history/tracking, assigned to the primary manager
        activity_type = self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)
        if activity_type:
            primary_user = notify_users[0] if notify_users else self.env.user
            self.activity_schedule(
                activity_type_id=activity_type.id,
                summary=title,
                note=message,
                user_id=primary_user.id,
                date_deadline=fields.Date.today(),
            )

    def _send_auto_mo_replenishment_alert(self, factory_type):
        self.ensure_one()
        if factory_type == "plastic":
            group_xml_id = "mrp_mps_manufacturing_type.group_mrp_manager_plastic"
        elif factory_type == "pharma":
            group_xml_id = "mrp_mps_manufacturing_type.group_mrp_manager_pharma"
        else:
            group_xml_id = "mrp_mps_manufacturing_type.group_mrp_manager_packaging"
        group = self.env.ref(group_xml_id, raise_if_not_found=False)
        
        notify_users = group.users.filtered(lambda u: u.active) if group else self.env['res.users']
        
        if not notify_users:
            notify_users = self.env.ref("mrp.group_mrp_manager").users.filtered(lambda u: u.active)
            
        if not notify_users:
            notify_users = self.env.user
            
        factory_name = "Plastic" if factory_type == "plastic" else ("Pharma" if factory_type == "pharma" else "Packaging")
        title = _("Auto MO Generation (%s)") % factory_name
        message = _("Manufacturing Order %s has been automatically generated via Replenishment (%s). Please review it.") % (self.name, factory_name)
        
        for user in notify_users:
            self.env["bus.bus"]._sendone(
                user.partner_id,
                "simple_notification",
                {
                    "type": "info",
                    "title": title,
                    "message": message,
                    "sticky": True,
                },
            )
            
        activity_type = self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)
        if activity_type:
            primary_user = notify_users[0] if notify_users else self.env.user
            self.activity_schedule(
                activity_type_id=activity_type.id,
                summary=title,
                note=message,
                user_id=primary_user.id,
                date_deadline=fields.Date.today(),
            )
