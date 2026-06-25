from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "rma_transform_return_lines")
class TestRmaTransformReturnLines(TransactionCase):

    def test_new_document_starts_blank_without_original_delivery(self):
        record = self.env["rma.transform.return"].create({})

        self.assertFalse(record.source_picking_id)
        self.assertFalse(record.source_move_id)
        self.assertFalse(record.product_from_id)
        self.assertEqual(len(record.line_ids), 0)

    def test_return_lines_are_source_of_truth(self):
        model = self.env["rma.transform.return"]
        line_model = self.env["rma.transform.return.line"]

        self.assertIn("line_ids", model._fields)
        self.assertIn("return_id", line_model._fields)
        self.assertIn("source_move_id", line_model._fields)
        self.assertIn("invoice_line_id", line_model._fields)
        self.assertIn("refund_amount", line_model._fields)

    def test_editing_return_line_does_not_reload_source_defaults(self):
        stock_location = self.env.ref("stock.stock_location_stock")
        customer_location = self.env.ref("stock.stock_location_customers")
        picking_type = self.env["stock.picking.type"].search([("code", "=", "outgoing")], limit=1)
        product_from = self.env["product.product"].create({"name": "RMA Test Sold Pack", "type": "consu"})
        product_to_a = self.env["product.product"].create({"name": "RMA Test Returned Piece A", "type": "consu"})
        product_to_b = self.env["product.product"].create({"name": "RMA Test Returned Piece B", "type": "consu"})
        rule_a = self.env["product.transform.rule"].create({
            "name": "RMA Test Rule A",
            "product_from_id": product_from.id,
            "product_to_id": product_to_a.id,
            "qty_to": 6.0,
        })
        rule_b = self.env["product.transform.rule"].create({
            "name": "RMA Test Rule B",
            "product_from_id": product_from.id,
            "product_to_id": product_to_b.id,
            "qty_to": 12.0,
        })
        picking = self.env["stock.picking"].create({
            "picking_type_id": picking_type.id,
            "location_id": stock_location.id,
            "location_dest_id": customer_location.id,
        })
        record = self.env["rma.transform.return"].create({})
        line = self.env["rma.transform.return.line"].with_context(skip_rma_transform_line_source_sync=True).create({
            "return_id": record.id,
            "source_picking_id": picking.id,
            "rule_id": rule_a.id,
            "product_from_id": product_from.id,
            "product_to_id": product_to_a.id,
            "qty_return": 1.0,
        })
        line = self.env["rma.transform.return.line"].browse(line.id)

        line.write({
            "rule_id": rule_b.id,
            "product_to_id": product_to_b.id,
            "qty_return": 7.0,
        })

        self.assertEqual(line.rule_id, rule_b)
        self.assertEqual(line.product_to_id, product_to_b)
        self.assertEqual(line.qty_return, 7.0)
