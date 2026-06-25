from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "mrp_mps_manufacturing_type")
class TestManualInternalTransferMerge(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.internal_type = cls.env.ref("stock.picking_type_internal")
        cls.stock_location = cls.env.ref("stock.stock_location_stock")
        cls.shopfloor_location = cls.env["stock.location"].create(
            {
                "name": "Manual Merge Shopfloor",
                "usage": "internal",
                "location_id": cls.stock_location.location_id.id,
            }
        )
        cls.customer_location = cls.env.ref("stock.stock_location_customers")
        cls.uom = cls.env.ref("uom.product_uom_unit")
        cls.product = cls.env["product.product"].create(
            {
                "name": "Manual Merge Component",
                "type": "consu",
            }
        )
        cls.finished_product = cls.env["product.product"].create(
            {
                "name": "Manual Merge Finished",
                "type": "consu",
            }
        )
        cls.partner = cls.env["res.partner"].create({"name": "Manual Merge Partner"})
        cls.so_type = cls.env["sale.sequence.type"].search([], limit=1)
        cls.bom = cls.env["mrp.bom"].create(
            {
                "product_tmpl_id": cls.finished_product.product_tmpl_id.id,
                "product_qty": 1.0,
                "product_uom_id": cls.uom.id,
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": cls.product.id,
                            "product_qty": 1.0,
                            "product_uom_id": cls.uom.id,
                        }
                    )
                ],
            }
        )

    def _create_internal_picking(self, name, qty=1.0, manufacturing_type="plastic"):
        picking = self.env["stock.picking"].create(
            {
                "name": name,
                "picking_type_id": self.internal_type.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.shopfloor_location.id,
                "company_id": self.company.id,
                "manufacturing_type": manufacturing_type,
            }
        )
        self.env["stock.move"].create(
            {
                "name": name,
                "product_id": self.product.id,
                "product_uom_qty": qty,
                "product_uom": self.uom.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.shopfloor_location.id,
                "picking_id": picking.id,
                "company_id": self.company.id,
            }
        )
        return picking

    def test_internal_mo_transfer_keeps_original_procurement_group(self):
        sale_group = self.env["procurement.group"].create({"name": "SO Manual Merge Group"})
        mo_group = self.env["procurement.group"].create({"name": "MO Manual Merge Group"})
        sale = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "so_type_id": self.so_type.id,
                "procurement_group_id": sale_group.id,
            }
        )
        self.env["mrp.production"].with_context(skip_auto_merge=True).create(
            {
                "product_id": self.finished_product.id,
                "product_qty": 1.0,
                "product_uom_id": self.uom.id,
                "bom_id": self.bom.id,
                "procurement_group_id": mo_group.id,
                "source_sale_order_id": sale.id,
            }
        )
        move = self.env["stock.move"].create(
            {
                "name": "MO Internal Transfer Move",
                "product_id": self.product.id,
                "product_uom_qty": 1.0,
                "product_uom": self.uom.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.shopfloor_location.id,
                "picking_type_id": self.internal_type.id,
                "group_id": mo_group.id,
                "company_id": self.company.id,
            }
        )

        self.assertFalse(move._get_mto_transfer_merge_group())
        move._assign_picking()
        self.assertEqual(move.group_id, mo_group)

    def test_manual_merge_moves_source_pickings_into_one_internal_transfer(self):
        first = self._create_internal_picking("IT/MANUAL/001", qty=2.0)
        second = self._create_internal_picking("IT/MANUAL/002", qty=3.0)

        wizard = self.env["stock.picking.manual.merge.wizard"].create(
            {"picking_ids": [Command.set((first | second).ids)]}
        )
        action = wizard.action_merge()

        self.assertEqual(action["res_id"], first.id)
        self.assertIn(first.state, ("confirmed", "assigned"))
        self.assertEqual(second.state, "cancel")
        self.assertEqual(len(first.move_ids), 1)
        self.assertEqual(sum(first.move_ids.mapped("product_uom_qty")), 5.0)
        self.assertEqual(first.manufacturing_type, "plastic")

    def test_manual_merge_consolidates_compatible_operation_lines(self):
        first = self._create_internal_picking("IT/MANUAL/LINE/001", qty=2.0)
        second = self._create_internal_picking("IT/MANUAL/LINE/002", qty=3.0)
        (first | second).action_confirm()
        first.move_ids.quantity = 2.0
        second.move_ids.quantity = 3.0

        wizard = self.env["stock.picking.manual.merge.wizard"].create(
            {"picking_ids": [Command.set((first | second).ids)]}
        )
        wizard.action_merge()

        self.assertEqual(len(first.move_ids), 1)
        self.assertEqual(first.move_ids.product_uom_qty, 5.0)
        self.assertEqual(first.move_ids.quantity, 5.0)
        self.assertEqual(first.move_ids.move_lines_count, 2)
        self.assertEqual(second.state, "cancel")

    def test_cancel_one_mo_keeps_shared_merged_transfer_for_remaining_mo(self):
        Production = self.env["mrp.production"].with_context(skip_auto_merge=True)
        first_mo = Production.create(
            {
                "product_id": self.finished_product.id,
                "product_qty": 1.0,
                "product_uom_id": self.uom.id,
                "bom_id": self.bom.id,
                "procurement_group_id": self.env["procurement.group"].create({"name": "MO Cancel One"}).id,
            }
        )
        second_mo = Production.create(
            {
                "product_id": self.finished_product.id,
                "product_qty": 1.0,
                "product_uom_id": self.uom.id,
                "bom_id": self.bom.id,
                "procurement_group_id": self.env["procurement.group"].create({"name": "MO Cancel Two"}).id,
            }
        )
        (first_mo | second_mo).action_confirm()
        first = self._create_internal_picking("IT/MANUAL/CANCEL/001", qty=1.0)
        second = self._create_internal_picking("IT/MANUAL/CANCEL/002", qty=1.0)
        first.move_ids.write({"move_dest_ids": [Command.link(first_mo.move_raw_ids.id)]})
        second.move_ids.write({"move_dest_ids": [Command.link(second_mo.move_raw_ids.id)]})
        (first | second).action_confirm()
        first.move_ids.quantity = 1.0
        second.move_ids.quantity = 1.0

        wizard = self.env["stock.picking.manual.merge.wizard"].create(
            {"picking_ids": [Command.set((first | second).ids)]}
        )
        wizard.action_merge()

        self.assertEqual(len(first.move_ids), 1)
        self.assertEqual(first.move_ids.product_uom_qty, 2.0)
        self.assertEqual(set(first.production_ids.ids), set((first_mo | second_mo).ids))

        first_mo.action_cancel()

        self.assertEqual(first_mo.state, "cancel")
        self.assertEqual(second_mo.state, "confirmed")
        self.assertNotEqual(first.state, "cancel")
        self.assertEqual(len(first.move_ids.filtered(lambda move: move.state != "cancel")), 1)
        self.assertEqual(first.move_ids.filtered(lambda move: move.state != "cancel").product_uom_qty, 1.0)

        second_mo.action_cancel()

        self.assertEqual(second_mo.state, "cancel")
        self.assertEqual(first.state, "cancel")

    def test_manual_merge_rejects_different_manufacturing_types(self):
        plastic = self._create_internal_picking("IT/MANUAL/PLASTIC", manufacturing_type="plastic")
        pharma = self._create_internal_picking("IT/MANUAL/PHARMA", manufacturing_type="pharma")
        wizard = self.env["stock.picking.manual.merge.wizard"].create(
            {"picking_ids": [Command.set((plastic | pharma).ids)]}
        )

        with self.assertRaises(UserError):
            wizard.action_merge()

    def test_admin_can_create_manual_merge_wizard(self):
        first = self._create_internal_picking("IT/MANUAL/ACL/001")
        second = self._create_internal_picking("IT/MANUAL/ACL/002")
        admin = self.env.ref("base.user_admin")

        wizard = self.env["stock.picking.manual.merge.wizard"].with_user(admin).create(
            {"picking_ids": [Command.set((first | second).ids)]}
        )

        self.assertEqual(wizard.picking_ids, first | second)

    def test_mo_action_opens_manual_merge_wizard_with_related_internal_transfers(self):
        first = self._create_internal_picking("IT/MANUAL/MO/001")
        second = self._create_internal_picking("IT/MANUAL/MO/002")
        Production = self.env["mrp.production"].with_context(skip_auto_merge=True)
        first_mo = Production.create(
            {
                "product_id": self.finished_product.id,
                "product_qty": 1.0,
                "product_uom_id": self.uom.id,
                "bom_id": self.bom.id,
                "procurement_group_id": self.env["procurement.group"].create({"name": "MO One"}).id,
            }
        )
        second_mo = Production.create(
            {
                "product_id": self.finished_product.id,
                "product_qty": 1.0,
                "product_uom_id": self.uom.id,
                "bom_id": self.bom.id,
                "procurement_group_id": self.env["procurement.group"].create({"name": "MO Two"}).id,
            }
        )
        first.move_ids.write({"raw_material_production_id": first_mo.id})
        second.move_ids.write({"raw_material_production_id": second_mo.id})

        action = (first_mo | second_mo).action_open_manual_merge_internal_transfers()

        self.assertEqual(action["res_model"], "stock.picking.manual.merge.wizard")
        self.assertEqual(set(action["context"]["default_picking_ids"][0][2]), set((first | second).ids))

    def test_mo_purchase_order_button_finds_merged_origin_purchase(self):
        Production = self.env["mrp.production"].with_context(skip_auto_merge=True)
        mo = Production.create(
            {
                "name": "GMP/MOPL/00193",
                "product_id": self.finished_product.id,
                "product_qty": 1.0,
                "product_uom_id": self.uom.id,
                "bom_id": self.bom.id,
                "procurement_group_id": self.env["procurement.group"].create({"name": "MO PO Link"}).id,
            }
        )
        vendor = self.env["res.partner"].create({"name": "MO Auto PO Vendor"})
        matching_po = self.env["purchase.order"].create(
            {
                "partner_id": vendor.id,
                "origin": "GMP/MOPL/00149, GMP/MOPL/00193",
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "name": self.product.display_name,
                            "product_qty": 1.0,
                            "product_uom": self.uom.id,
                            "price_unit": 10.0,
                            "date_planned": fields.Datetime.now(),
                        }
                    )
                ],
            }
        )
        self.env["purchase.order"].create(
            {
                "partner_id": vendor.id,
                "origin": "GMP/MOPL/001930",
            }
        )

        self.assertEqual(mo.purchase_order_count, 1)

        action = mo.action_view_purchase_orders()

        self.assertEqual(action["res_model"], "purchase.order")
        self.assertEqual(action["res_id"], matching_po.id)
