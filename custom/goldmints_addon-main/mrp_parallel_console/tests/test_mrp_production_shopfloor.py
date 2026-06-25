from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "mrp_parallel_console")
class TestMrpProductionShopfloor(TransactionCase):
    def test_new_mo_is_hidden_from_shopfloor_by_default(self):
        production = self.env["mrp.production"].new({})

        self.assertTrue(production.hide_from_shopfloor)
        self.assertFalse(production.show_on_shopfloor)

    def test_shopfloor_visible_inverse_updates_hidden_flag(self):
        production = self.env["mrp.production"].new({})

        production.show_on_shopfloor = True
        production._inverse_show_on_shopfloor()

        self.assertFalse(production.hide_from_shopfloor)

    def test_overproduction_transfer_creates_all_short_component_lines(self):
        warehouse = self.env["stock.warehouse"].search([("company_id", "=", self.env.company.id)], limit=1)
        stock_location = warehouse.lot_stock_id
        production_location = self.env["stock.location"].search([("usage", "=", "production")], limit=1)
        if not production_location:
            production_location = self.env["stock.location"].create(
                {
                    "name": "Console Transfer Production",
                    "usage": "production",
                    "company_id": self.env.company.id,
                }
            )
        shopfloor_location = self.env["stock.location"].create(
            {
                "name": "Console Transfer Shopfloor",
                "usage": "internal",
                "location_id": stock_location.location_id.id,
                "company_id": self.env.company.id,
            }
        )
        route = self.env["stock.route"].create(
            {
                "name": "Console Transfer Route",
                "product_selectable": True,
                "company_id": self.env.company.id,
            }
        )
        internal_type = self.env["stock.picking.type"].search(
            [
                ("code", "=", "internal"),
                ("warehouse_id", "=", warehouse.id),
            ],
            limit=1,
        )
        self.env["stock.rule"].create(
            {
                "name": "Console Transfer Rule",
                "route_id": route.id,
                "action": "pull",
                "procure_method": "make_to_stock",
                "location_src_id": stock_location.id,
                "location_dest_id": shopfloor_location.id,
                "picking_type_id": internal_type.id,
                "company_id": self.env.company.id,
            }
        )
        finished = self.env["product.product"].create(
            {
                "name": "Console Transfer Finished",
                "type": "consu",
            }
        )
        raw_a = self.env["product.product"].create(
            {
                "name": "Console Transfer Raw A",
                "type": "consu",
                "route_ids": [Command.set(route.ids)],
            }
        )
        raw_b = self.env["product.product"].create(
            {
                "name": "Console Transfer Raw B",
                "type": "consu",
                "route_ids": [Command.set(route.ids)],
            }
        )
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": finished.product_tmpl_id.id,
                "product_qty": 1.0,
                "product_uom_id": finished.uom_id.id,
            }
        )
        production = self.env["mrp.production"].create(
            {
                "product_id": finished.id,
                "product_qty": 1.0,
                "product_uom_id": finished.uom_id.id,
                "bom_id": bom.id,
                "location_src_id": shopfloor_location.id,
                "location_dest_id": stock_location.id,
                "picking_type_id": warehouse.manu_type_id.id,
            }
        )
        production.write(
            {
                "move_raw_ids": [
                    Command.create(
                        {
                            "name": raw_a.display_name,
                            "product_id": raw_a.id,
                            "product_uom_qty": 28.16,
                            "product_uom": raw_a.uom_id.id,
                            "location_id": shopfloor_location.id,
                            "location_dest_id": production_location.id,
                        }
                    ),
                    Command.create(
                        {
                            "name": raw_b.display_name,
                            "product_id": raw_b.id,
                            "product_uom_qty": 0.41,
                            "product_uom": raw_b.uom_id.id,
                            "location_id": shopfloor_location.id,
                            "location_dest_id": production_location.id,
                        }
                    ),
                ]
            }
        )
        raw_a_move = production.move_raw_ids.filtered(lambda move: move.product_id == raw_a)
        raw_b_move = production.move_raw_ids.filtered(lambda move: move.product_id == raw_b)
        raw_a_move.quantity = 28.16
        raw_b_move.quantity = 0.27

        pickings = production._console_create_overproduction_transfer()

        self.assertEqual(len(pickings), 1)
        self.assertEqual(pickings.location_id, stock_location)
        self.assertEqual(pickings.location_dest_id, shopfloor_location)
        qty_by_product = {move.product_id: move.product_uom_qty for move in pickings.move_ids}
        self.assertAlmostEqual(qty_by_product[raw_a], 28.16)
        self.assertAlmostEqual(qty_by_product[raw_b], 0.41)
        self.assertTrue(all(move.raw_material_production_id == production for move in pickings.move_ids))

        self.assertFalse(production._console_create_overproduction_transfer())
