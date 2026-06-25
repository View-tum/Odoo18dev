from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "sale_auto_warehouse_van_sales")
class TestVanSaleLocation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.company.id)], limit=1)
        customer_vals = {"name": "Van Sale Customer"}
        if "approval_state" in cls.env["res.partner"]._fields:
            customer_vals["approval_state"] = "approved"
        cls.customer = cls.env["res.partner"].create(customer_vals)
        cls.car_location = cls.env["stock.location"].create(
            {
                "name": "CARSALE TEST",
                "usage": "internal",
                "location_id": cls.warehouse.lot_stock_id.id,
                "company_id": cls.company.id,
            }
        )
        cls.other_location = cls.env["stock.location"].create(
            {
                "name": "OTHER VAN SOURCE TEST",
                "usage": "internal",
                "location_id": cls.warehouse.lot_stock_id.id,
                "company_id": cls.company.id,
            }
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Van Sale Product",
                "type": "consu",
            }
        )
        if "approval_state" in cls.product.product_tmpl_id._fields:
            cls.product.product_tmpl_id.approval_state = "approved"
        cls.so_type = cls.env["sale.sequence.type"].search([], limit=1)
        group = cls.env.ref("sale_auto_warehouse_van_sales.group_van_sales")
        cls.van_user = cls.env["res.users"].create(
            {
                "name": "Van Sale Test User",
                "login": "van_sale_location_test",
                "email": "van_sale_location_test@example.com",
                "groups_id": [Command.set((group | cls.env.ref("sales_team.group_sale_salesman")).ids)],
                "van_sale_location_id": cls.car_location.id,
            }
        )
        cls.location_only_user = cls.env["res.users"].create(
            {
                "name": "Van Source Location Only User",
                "login": "van_source_location_only_test",
                "email": "van_source_location_only_test@example.com",
                "groups_id": [Command.set([cls.env.ref("stock.group_stock_user").id])],
                "van_sale_location_id": cls.car_location.id,
            }
        )

    def _create_sale_order(self, user):
        order = self.env["sale.order"].with_user(user).create(
            {
                "partner_id": self.customer.id,
                "warehouse_id": self.warehouse.id,
                "so_type_id": self.so_type.id,
                "date_order": fields.Datetime.now(),
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 1.0,
                            "price_unit": 10.0,
                            "tax_id": [Command.clear()],
                        }
                    )
                ],
            }
        )
        order.with_user(user).action_confirm()
        return order

    def test_van_sale_confirmation_sets_delivery_source_to_user_car_location(self):
        order = self._create_sale_order(self.van_user)
        picking = order.picking_ids.filtered(lambda p: p.picking_type_id.code == "outgoing")[:1]

        self.assertTrue(picking)
        self.assertEqual(picking.location_id, self.car_location)
        self.assertTrue(all(move.location_id == self.car_location for move in picking.move_ids))
        self.assertTrue(all(line.location_id == self.car_location for line in picking.move_line_ids))

    def test_van_sale_delivery_source_syncs_detailed_operation_source(self):
        order = self._create_sale_order(self.van_user)
        picking = order.picking_ids.filtered(lambda p: p.picking_type_id.code == "outgoing")[:1]
        move = picking.move_ids[:1]
        move_line = self.env["stock.move.line"].create(
            {
                "picking_id": picking.id,
                "move_id": move.id,
                "product_id": self.product.id,
                "product_uom_id": self.product.uom_id.id,
                "quantity": 1.0,
                "location_id": self.other_location.id,
                "location_dest_id": picking.location_dest_id.id,
                "company_id": self.company.id,
            }
        )

        picking._sync_van_sales_operation_move_locations()

        self.assertEqual(move.location_id, self.car_location)
        self.assertEqual(move_line.location_id, self.car_location)

    def test_picking_source_write_syncs_stock_move_and_detailed_operation_source(self):
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.warehouse.out_type_id.id,
                "location_id": self.warehouse.out_type_id.default_location_src_id.id,
                "location_dest_id": self.warehouse.out_type_id.default_location_dest_id.id,
            }
        )
        move = self.env["stock.move"].create(
            {
                "name": self.product.display_name,
                "picking_id": picking.id,
                "product_id": self.product.id,
                "product_uom_qty": 1.0,
                "product_uom": self.product.uom_id.id,
                "location_id": picking.location_id.id,
                "location_dest_id": picking.location_dest_id.id,
                "company_id": self.company.id,
            }
        )
        move_line = self.env["stock.move.line"].create(
            {
                "picking_id": picking.id,
                "move_id": move.id,
                "product_id": self.product.id,
                "product_uom_id": self.product.uom_id.id,
                "quantity": 1.0,
                "location_id": picking.location_id.id,
                "location_dest_id": picking.location_dest_id.id,
                "company_id": self.company.id,
            }
        )

        picking.write({"location_id": self.car_location.id})

        self.assertEqual(picking.location_id, self.car_location)
        self.assertEqual(move.location_id, self.car_location)
        self.assertTrue(all(line.location_id == self.car_location for line in move.move_line_ids))

    def test_open_move_details_syncs_existing_mismatched_source(self):
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.warehouse.out_type_id.id,
                "location_id": self.car_location.id,
                "location_dest_id": self.warehouse.out_type_id.default_location_dest_id.id,
            }
        )
        move = self.env["stock.move"].create(
            {
                "name": self.product.display_name,
                "picking_id": picking.id,
                "product_id": self.product.id,
                "product_uom_qty": 1.0,
                "product_uom": self.product.uom_id.id,
                "location_id": self.other_location.id,
                "location_dest_id": picking.location_dest_id.id,
                "company_id": self.company.id,
            }
        )
        self.env["stock.move.line"].create(
            {
                "picking_id": picking.id,
                "move_id": move.id,
                "product_id": self.product.id,
                "product_uom_id": self.product.uom_id.id,
                "quantity": 1.0,
                "location_id": self.other_location.id,
                "location_dest_id": picking.location_dest_id.id,
                "company_id": self.company.id,
            }
        )

        action = move.action_show_details()

        self.assertEqual(action["res_id"], move.id)
        self.assertEqual(move.location_id, self.car_location)
        self.assertTrue(all(line.location_id == self.car_location for line in move.move_line_ids))

    def test_picking_web_read_syncs_existing_mismatched_source_before_ui_load(self):
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.warehouse.out_type_id.id,
                "location_id": self.car_location.id,
                "location_dest_id": self.warehouse.out_type_id.default_location_dest_id.id,
            }
        )
        move = self.env["stock.move"].create(
            {
                "name": self.product.display_name,
                "picking_id": picking.id,
                "product_id": self.product.id,
                "product_uom_qty": 1.0,
                "product_uom": self.product.uom_id.id,
                "location_id": self.other_location.id,
                "location_dest_id": picking.location_dest_id.id,
                "company_id": self.company.id,
            }
        )
        self.env["stock.move.line"].create(
            {
                "picking_id": picking.id,
                "move_id": move.id,
                "product_id": self.product.id,
                "product_uom_id": self.product.uom_id.id,
                "quantity": 1.0,
                "location_id": self.other_location.id,
                "location_dest_id": picking.location_dest_id.id,
                "company_id": self.company.id,
            }
        )

        picking.web_read(
            {
                "location_id": {},
                "move_ids_without_package": {
                    "fields": {
                        "location_id": {},
                        "move_line_ids": {"fields": {"location_id": {}, "quantity": {}}},
                    }
                },
            }
        )

        self.assertEqual(move.location_id, self.car_location)
        self.assertTrue(all(line.location_id == self.car_location for line in move.move_line_ids))

    def test_picking_web_read_keeps_existing_matching_detailed_operation(self):
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.warehouse.out_type_id.id,
                "location_id": self.car_location.id,
                "location_dest_id": self.warehouse.out_type_id.default_location_dest_id.id,
            }
        )
        move = self.env["stock.move"].create(
            {
                "name": self.product.display_name,
                "picking_id": picking.id,
                "product_id": self.product.id,
                "product_uom_qty": 1.0,
                "product_uom": self.product.uom_id.id,
                "location_id": self.car_location.id,
                "location_dest_id": picking.location_dest_id.id,
                "company_id": self.company.id,
            }
        )
        move_line = self.env["stock.move.line"].create(
            {
                "picking_id": picking.id,
                "move_id": move.id,
                "product_id": self.product.id,
                "product_uom_id": self.product.uom_id.id,
                "quantity": 1.0,
                "location_id": self.car_location.id,
                "location_dest_id": picking.location_dest_id.id,
                "company_id": self.company.id,
            }
        )

        picking.web_read(
            {
                "location_id": {},
                "move_ids_without_package": {
                    "fields": {
                        "location_id": {},
                        "move_line_ids": {"fields": {"location_id": {}, "quantity": {}}},
                    }
                },
            }
        )

        self.assertTrue(move_line.exists())
        self.assertEqual(move.move_line_ids, move_line)

    def test_van_sale_validation_blocks_wrong_source_location(self):
        order = self._create_sale_order(self.van_user)
        picking = order.picking_ids.filtered(lambda p: p.picking_type_id.code == "outgoing")[:1]
        picking.write({"location_id": self.other_location.id})
        picking.move_ids.write({"location_id": self.other_location.id})

        with self.assertRaises(UserError):
            picking.with_user(self.van_user).button_validate()

    def test_van_sale_validation_blocks_wrong_detailed_operation_source(self):
        order = self._create_sale_order(self.van_user)
        picking = order.picking_ids.filtered(lambda p: p.picking_type_id.code == "outgoing")[:1]
        move = picking.move_ids[:1]
        self.env["stock.move.line"].create(
            {
                "picking_id": picking.id,
                "move_id": move.id,
                "product_id": self.product.id,
                "product_uom_id": self.product.uom_id.id,
                "quantity": 1.0,
                "location_id": self.other_location.id,
                "location_dest_id": picking.location_dest_id.id,
                "company_id": self.company.id,
            }
        )

        with self.assertRaises(UserError):
            picking.with_user(self.van_user).button_validate()

    def test_internal_transfer_defaults_source_from_configured_user_location(self):
        picking_model = self.env["stock.picking"].with_user(self.location_only_user).with_context(
            default_picking_type_id=self.warehouse.int_type_id.id
        )

        defaults = picking_model.default_get(["picking_type_id", "location_id", "location_dest_id"])

        self.assertEqual(defaults["location_id"], self.car_location.id)

    def test_incoming_transfer_defaults_destination_from_configured_user_location(self):
        picking_model = self.env["stock.picking"].with_user(self.location_only_user).with_context(
            default_picking_type_id=self.warehouse.in_type_id.id
        )

        defaults = picking_model.default_get(["picking_type_id", "location_id", "location_dest_id"])

        self.assertEqual(defaults["location_dest_id"], self.car_location.id)

    def test_outgoing_transfer_defaults_source_from_configured_user_location(self):
        picking_model = self.env["stock.picking"].with_user(self.location_only_user).with_context(
            default_picking_type_id=self.warehouse.out_type_id.id
        )

        defaults = picking_model.default_get(["picking_type_id", "location_id", "location_dest_id"])

        self.assertEqual(defaults["location_id"], self.car_location.id)

    def test_internal_transfer_create_uses_configured_user_location_when_source_is_default(self):
        picking = self.env["stock.picking"].with_user(self.location_only_user).create(
            {
                "picking_type_id": self.warehouse.int_type_id.id,
                "location_id": self.warehouse.int_type_id.default_location_src_id.id,
                "location_dest_id": self.warehouse.int_type_id.default_location_dest_id.id,
            }
        )

        self.assertEqual(picking.location_id, self.car_location)

    def test_incoming_transfer_create_uses_configured_user_location_when_destination_is_default(self):
        picking = self.env["stock.picking"].with_user(self.location_only_user).create(
            {
                "picking_type_id": self.warehouse.in_type_id.id,
                "location_id": self.warehouse.in_type_id.default_location_src_id.id,
                "location_dest_id": self.warehouse.in_type_id.default_location_dest_id.id,
            }
        )

        self.assertEqual(picking.location_dest_id, self.car_location)

    def test_outgoing_transfer_create_uses_configured_user_location_when_source_is_default(self):
        picking = self.env["stock.picking"].with_user(self.location_only_user).create(
            {
                "picking_type_id": self.warehouse.out_type_id.id,
                "location_id": self.warehouse.out_type_id.default_location_src_id.id,
                "location_dest_id": self.warehouse.out_type_id.default_location_dest_id.id,
            }
        )

        self.assertEqual(picking.location_id, self.car_location)

    def test_internal_transfer_create_keeps_explicit_source_location(self):
        picking = self.env["stock.picking"].with_user(self.location_only_user).create(
            {
                "picking_type_id": self.warehouse.int_type_id.id,
                "location_id": self.other_location.id,
                "location_dest_id": self.warehouse.int_type_id.default_location_dest_id.id,
            }
        )

        self.assertEqual(picking.location_id, self.other_location)

    def test_incoming_transfer_create_keeps_explicit_destination_location(self):
        picking = self.env["stock.picking"].with_user(self.location_only_user).create(
            {
                "picking_type_id": self.warehouse.in_type_id.id,
                "location_id": self.warehouse.in_type_id.default_location_src_id.id,
                "location_dest_id": self.other_location.id,
            }
        )

        self.assertEqual(picking.location_dest_id, self.other_location)
