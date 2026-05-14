from odoo import Command
from odoo.tests.common import TransactionCase


class TestStockMoveLotDisplay(TransactionCase):
    def test_compute_handles_unsaved_move_lines(self):
        move = self.env['stock.move'].new({
            'name': 'TEST MOVE',
            'product_uom_qty': 1,
            'quantity': 1,
            'move_line_ids': [
                Command.create({'lot_name': 'LOT-A', 'quantity': 1}),
                Command.create({'lot_name': 'LOT-B', 'quantity': 1}),
            ],
        })

        self.assertEqual(move.gm_lot_display, 'LOT-A, LOT-B')
