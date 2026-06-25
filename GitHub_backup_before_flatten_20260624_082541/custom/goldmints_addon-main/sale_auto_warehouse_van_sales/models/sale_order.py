from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _default_is_van_sales_user(self):
        return self.env.user.has_group("sale_auto_warehouse_van_sales.group_van_sales")

    is_van_sales_user = fields.Boolean(
        string="Is Van Sales User",
        default=_default_is_van_sales_user,
        store=False,
        compute="_compute_is_van_sales_user",
    )

    @api.depends_context('uid')
    def _compute_is_van_sales_user(self):
        is_van = self.env.user.has_group("sale_auto_warehouse_van_sales.group_van_sales")
        for rec in self:
            rec.is_van_sales_user = is_van

    def _van_sales_target_warehouse(self):
        Wh = self.env["stock.warehouse"]
        icp = self.env["ir.config_parameter"].sudo()
        wh_id_param = icp.get_param("sale_auto_warehouse_van_sales.warehouse_id")
        wh = False
        if wh_id_param:
            try:
                wh_id = int(wh_id_param)
                wh = Wh.browse(wh_id).exists()
            except Exception:
                wh = False
        if not wh:
            wh = Wh.browse(2).exists()
        return wh

    def _van_sales_target_location(self, user=None):
        user = user or self.env.user
        location = user.van_sale_location_id
        if location:
            return location
        if "allowed_location_ids" in user._fields:
            car_locations = user.allowed_location_ids.filtered(
                lambda loc: loc.usage == "internal" and "CARSALE" in (loc.complete_name or loc.name or "").upper()
            )
            if len(car_locations) == 1:
                return car_locations
        return self.env["stock.location"]

    def _apply_van_sales_delivery_source(self):
        for order in self:
            user = order.user_id or self.env.user
            if not user.has_group("sale_auto_warehouse_van_sales.group_van_sales"):
                continue
            location = order._van_sales_target_location(user)
            if not location:
                continue
            pickings = order.picking_ids.filtered(lambda picking: picking.picking_type_id.code == "outgoing" and picking.state not in ("done", "cancel"))
            for picking in pickings:
                picking.write({"location_id": location.id})

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        user = self.env.user
        is_van = user.has_group("sale_auto_warehouse_van_sales.group_van_sales")
        res["is_van_sales_user"] = is_van
        if is_van:
            warehouse = self._van_sales_target_warehouse()
            if warehouse:
                res["warehouse_id"] = warehouse.id
        return res

    @api.model_create_multi
    def create(self, vals_list):
        user = self.env.user
        if user.has_group("sale_auto_warehouse_van_sales.group_van_sales"):
            warehouse = self._van_sales_target_warehouse()
            if warehouse:
                for vals in vals_list:
                    vals["warehouse_id"] = warehouse.id
        return super().create(vals_list)

    def write(self, vals):
        if "warehouse_id" in vals and self.env.user.has_group(
            "sale_auto_warehouse_van_sales.group_van_sales"
        ):
            warehouse = self._van_sales_target_warehouse()
            if warehouse:
                vals["warehouse_id"] = warehouse.id
        return super().write(vals)

    def action_confirm(self):
        res = super().action_confirm()
        self._apply_van_sales_delivery_source()
        return res


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    is_van_sales_user = fields.Boolean(
        related="order_id.is_van_sales_user",
        string="Is Van Sales User",
    )
