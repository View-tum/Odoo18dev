from odoo import models, fields, api, _


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        for order in orders:
            # Check if PO is created from replenishment (MTO/MTS)
            # Origin often starts with OP/ for reordering rules
            is_replenishment = False
            if order.origin:
                if any(x in order.origin for x in ["OP/", "Replenishment", "MTO"]):
                    is_replenishment = True

            if is_replenishment:
                order._check_important_po_notification()
        return orders

    def _check_important_po_notification(self):
        self.ensure_one()
        # Find products in this PO that are marked as 'Important'
        important_lines = self.order_line.filtered(
            lambda line: line.product_id.x_important_notify
        )
        if not important_lines:
            return

        # Separate notifications by factory type
        plastic_products = important_lines.filtered(
            lambda line: line.product_id.manufacturing_type == "plastic"
        )
        pharma_products = important_lines.filtered(
            lambda line: line.product_id.manufacturing_type == "pharma"
        )
        packaging_products = important_lines.filtered(
            lambda line: line.product_id.manufacturing_type == "packaging"
        )

        if plastic_products:
            self._send_po_popup_alert("plastic", plastic_products)
        if pharma_products:
            self._send_po_popup_alert("pharma", pharma_products)
        if packaging_products:
            self._send_po_popup_alert("packaging", packaging_products)

    def _send_po_popup_alert(self, factory_type, lines):
        self.ensure_one()
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
            notify_users = self.env.ref("mrp.group_mrp_manager").users.filtered(
                lambda u: u.active
            )

        if not notify_users:
            return

        factory_label = dict(
            self.env["product.template"]
            ._fields["manufacturing_type"]
            ._description_selection(self.env)
        ).get(factory_type, factory_type.capitalize())

        title = _("URGENT REPLENISHMENT: %s") % factory_label.upper()
        product_names = ", ".join(lines.mapped("product_id.display_name"))
        message = _(
            "Purchase Order %s has been created for critical items: %s. "
            "Please follow up on this replenishment immediately!"
        ) % (self.name, product_names)

        for user in notify_users:
            self.env["bus.bus"]._sendone(
                user.partner_id,
                "simple_notification",
                {
                    "type": "warning",
                    "title": title,
                    "message": message,
                    "sticky": True,
                },
            )

        # Create activity for tracking
        activity_type = self.env.ref("mail.mail_activity_data_todo")
        for user in notify_users:
            self.activity_schedule(
                activity_type_id=activity_type.id,
                summary=title,
                note=message,
                user_id=user.id,
                date_deadline=fields.Date.today(),
            )

    def _send_auto_po_replenishment_alert(self, factory_type):
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
        title = _("Auto PO Replenishment (%s)") % factory_name
        message = _("Purchase Order %s has been automatically generated or updated via Replenishment for %s materials. Please review it.") % (self.name, factory_name)
        
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
                self.activity_schedule(
                    activity_type_id=activity_type.id,
                    summary=title,
                    note=message,
                    user_id=user.id,
                    date_deadline=fields.Date.today(),
                )
