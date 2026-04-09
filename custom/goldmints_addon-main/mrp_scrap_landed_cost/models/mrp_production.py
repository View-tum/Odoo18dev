from odoo import fields, models
from odoo.exceptions import UserError


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    cost_finalized = fields.Boolean(
        string="Cost Finalized",
        default=False,
        copy=False,
        help="Marked as true when scrap costs have been absorbed via Landed Cost",
    )

    def _check_fg_not_used(self):
        for mo in self:
            moves = mo.move_finished_ids.filtered(
                lambda m: m.state == "done" and m.quantity > 0
            )
            for move in moves:
                val_layers = move.stock_valuation_layer_ids
                if any(vl.remaining_qty < vl.quantity for vl in val_layers):
                    raise UserError(
                        f"Finished goods for {mo.name} have already been used, delivered, or moved. "
                        "Cannot apply landed cost to used inventory layers."
                    )

    def _get_unabsorbed_scraps(self):
        self.ensure_one()
        return self.env["stock.scrap"].search(
            [
                "|",
                ("production_id", "=", self.id),
                ("workorder_id.production_id", "=", self.id),
                ("state", "=", "done"),
                ("landed_cost_id", "=", False),
                ("company_id", "=", self.company_id.id),
            ]
        )

    def _get_unabsorbed_scrap_cost(self, scraps=None):
        self.ensure_one()
        scraps = scraps or self._get_unabsorbed_scraps()
        total_cost = 0.0
        for scrap in scraps:
            scrap_val = 0.0
            if scrap.move_ids:
                for move in scrap.move_ids:
                    if move.stock_valuation_layer_ids:
                        scrap_val += sum(
                            move.stock_valuation_layer_ids.mapped(
                                lambda layer: abs(layer.value)
                            )
                        )
            if not scrap_val:
                scrap_val = scrap.product_id.standard_price * scrap.scrap_qty
            total_cost += scrap_val
        return total_cost

    def button_mark_done(self):
        res = super().button_mark_done()
        for mo in self.filtered(lambda p: p.state == "done"):
            try:
                with self.env.cr.savepoint():
                    mo.sudo()._auto_allocate_scrap_cost()
            except Exception as e:
                # Do not block MO completion if scrap cost auto-allocation fails.
                mo.message_post(
                    body=f"Auto-Allocate Scrap Cost Failed: {str(e)}"
                )
        return res

    def _auto_allocate_scrap_cost(self):
        self.ensure_one()
        scraps = self._get_unabsorbed_scraps()
        if not scraps:
            return

        self._check_fg_not_used()
        total_cost = self._get_unabsorbed_scrap_cost(scraps)
        if total_cost <= 0:
            return

        service_product = self.company_id.mrp_scrap_landed_cost_product_id
        if not service_product:
            self.message_post(
                body="Auto-Allocate Scrap Cost Skipped: Scrap Landed Cost Service product is not configured in settings."
            )
            return

        account_id = (
            service_product.property_account_expense_id.id
            or service_product.categ_id.property_account_expense_categ_id.id
        )
        if not account_id:
            self.message_post(
                body="Auto-Allocate Scrap Cost Skipped: No Expense Account defined on the Scrap Landed Cost product or its category."
            )
            return

        landed_cost = self.env["stock.landed.cost"].create(
            {
                "target_model": "manufacturing",
                "mrp_production_ids": [(4, self.id)],
                "cost_lines": [
                    (
                        0,
                        0,
                        {
                            "product_id": service_product.id,
                            "name": f"Auto-Allocated Scrap Cost for {self.name}",
                            "account_id": account_id,
                            # The landed cost override recomputes the final scrap amount
                            # from stock.scrap before validation.
                            "price_unit": total_cost,
                            "split_method": service_product.split_method_landed_cost
                            or "equal",
                        },
                    )
                ],
            }
        )
        landed_cost.compute_landed_cost()
        landed_cost.button_validate()

        scraps.write({"landed_cost_id": landed_cost.id})
        self.cost_finalized = True
        self.message_post(
            body=(
                f"Scrap Cost ({total_cost:,.2f}) has been auto-allocated via "
                f"Landed Cost <a href=# data-oe-model=stock.landed.cost "
                f"data-oe-id={landed_cost.id}>{landed_cost.name}</a>."
            )
        )
