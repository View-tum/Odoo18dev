from odoo import api, fields, models


class StockQuant(models.Model):
    _inherit = "stock.quant"

    migration_real_cost = fields.Float(
        string="Force Import Cost",
        digits="Product Price",
        help="Use this field to force specific FIFO cost during import",
    )

    def _get_inventory_move_values(self, qty, location_id, location_dest_id, **kwargs):
        res = super()._get_inventory_move_values(qty, location_id, location_dest_id, **kwargs)
        if location_id.usage == 'inventory' and self.migration_real_cost > 0:
            res['price_unit'] = self.migration_real_cost
        return res

    @api.model
    def _get_inventory_fields_write(self):
        res = super()._get_inventory_fields_write()
        res.append('migration_real_cost')
        return res
