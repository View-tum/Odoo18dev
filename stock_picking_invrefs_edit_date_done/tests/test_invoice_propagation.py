from odoo import fields
from odoo.tests import common


class TestInvoicePropagation(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Picking = cls.env["stock.picking"]
        cls.Move = cls.env["stock.move"]
        cls.Product = cls.env["product.product"]

        cls.picking_type_in = cls.env.ref("stock.picking_type_in")
        cls.picking_type_internal = cls.env.ref("stock.picking_type_internal")
        cls.supplier_loc = cls.env.ref("stock.stock_location_suppliers")
        cls.input_loc = cls.env.ref("stock.stock_location_input")
        cls.stock_loc = cls.env.ref("stock.stock_location_stock")
        cls.uom_unit = cls.env.ref("uom.product_uom_unit")

        cls.product = cls.Product.create({
            "name": "Invoice Propagation Product",
            "type": "product",
            "uom_id": cls.uom_unit.id,
            "uom_po_id": cls.uom_unit.id,
        })

        cls.picking_type_in.write({
            "require_invoice_info": True,
            "propagate_invoice_info": True,
        })
        cls.picking_type_internal.write({
            "require_invoice_info": True,
            "propagate_invoice_info": False,
        })

    def _create_receipt_with_move(self):
        picking = self.Picking.create({
            "picking_type_id": self.picking_type_in.id,
            "location_id": self.supplier_loc.id,
            "location_dest_id": self.input_loc.id,
            "move_ids_without_package": [(0, 0, {
                "name": "Receipt Move",
                "product_id": self.product.id,
                "product_uom": self.uom_unit.id,
                "product_uom_qty": 1.0,
                "location_id": self.supplier_loc.id,
                "location_dest_id": self.input_loc.id,
            })],
        })
        return picking, picking.move_ids_without_package

    def _create_storage_from_moves(self, origin_moves, procurement_group=None, with_links=True):
        picking_vals = {
            "picking_type_id": self.picking_type_internal.id,
            "location_id": self.input_loc.id,
            "location_dest_id": self.stock_loc.id,
        }
        if procurement_group:
            picking_vals["group_id"] = procurement_group.id
        storage = self.Picking.create(picking_vals)

        move_vals = {
            "name": "Storage Move",
            "product_id": self.product.id,
            "product_uom": self.uom_unit.id,
            "product_uom_qty": 1.0,
            "location_id": self.input_loc.id,
            "location_dest_id": self.stock_loc.id,
            "picking_id": storage.id,
        }
        if with_links:
            move_vals["move_orig_ids"] = [(6, 0, origin_moves.ids)]
        self.Move.create(move_vals)
        return storage

    def test_invoice_propagates_to_existing_storage(self):
        receipt, receipt_moves = self._create_receipt_with_move()
        storage = self._create_storage_from_moves(receipt_moves)

        values = {
            "invoice_reference": "INV-001",
            "invoice_date": fields.Date.today(),
        }
        receipt.write(values)
        storage.invalidate_cache(["invoice_reference", "invoice_date"])
        self.assertEqual(storage.invoice_reference, values["invoice_reference"])
        self.assertEqual(storage.invoice_date, values["invoice_date"])

    def test_storage_created_after_invoice_gets_prefilled(self):
        receipt, receipt_moves = self._create_receipt_with_move()
        values = {
            "invoice_reference": "INV-002",
            "invoice_date": fields.Date.today(),
        }
        receipt.write(values)

        storage = self._create_storage_from_moves(receipt_moves)
        storage.invalidate_cache(["invoice_reference", "invoice_date"])
        self.assertEqual(storage.invoice_reference, values["invoice_reference"])
        self.assertEqual(storage.invoice_date, values["invoice_date"])

    def test_group_fallback_prefills_invoice(self):
        receipt, _ = self._create_receipt_with_move()
        values = {
            "invoice_reference": "INV-003",
            "invoice_date": fields.Date.today(),
        }
        receipt.write(values)
        group = self.env["procurement.group"].create({"name": "Fallback Group"})
        receipt.group_id = group.id

        storage = self._create_storage_from_moves(self.env["stock.move"], procurement_group=group, with_links=False)
        storage.invalidate_cache(["invoice_reference", "invoice_date"])
        self.assertEqual(storage.invoice_reference, values["invoice_reference"])
        self.assertEqual(storage.invoice_date, values["invoice_date"])
