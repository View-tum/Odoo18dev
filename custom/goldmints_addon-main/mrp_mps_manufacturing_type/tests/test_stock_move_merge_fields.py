from odoo import Command
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "mrp_mps_manufacturing_type")
class TestStockMoveMergeFields(TransactionCase):
    def test_merge_moves_fields_preserves_external_links_and_excludes_internal_links(self):
        product = self.env["product.product"].create(
            {
                "name": "Merge Fields API Test Product",
                "type": "consu",
            }
        )
        source_location = self.env.ref("stock.stock_location_stock")
        dest_location = self.env.ref("stock.stock_location_customers")
        moves = self.env["stock.move"].create(
            [
                {
                    "name": name,
                    "product_id": product.id,
                    "product_uom_qty": 1.0,
                    "product_uom": product.uom_id.id,
                    "location_id": source_location.id,
                    "location_dest_id": dest_location.id,
                }
                for name in (
                    "External Upstream",
                    "Merge Candidate One",
                    "Merge Candidate Two",
                    "External Downstream",
                )
            ]
        )
        external_upstream, candidate_one, candidate_two, external_downstream = moves
        candidate_one.move_orig_ids = [
            Command.link(external_upstream.id),
            Command.link(candidate_two.id),
        ]
        candidate_one.move_dest_ids = [
            Command.link(candidate_two.id),
            Command.link(external_downstream.id),
        ]

        vals = (candidate_one | candidate_two)._merge_moves_fields()

        dest_ids = {command[1] for command in vals["move_dest_ids"]}
        orig_ids = {command[1] for command in vals["move_orig_ids"]}
        self.assertEqual(dest_ids, {external_downstream.id})
        self.assertEqual(orig_ids, {external_upstream.id})
