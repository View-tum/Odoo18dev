from odoo import api, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

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

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        user = self.env.user
        if user.has_group("sale_auto_warehouse_van_sales.group_van_sales"):
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
