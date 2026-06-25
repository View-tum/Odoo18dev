import logging

from odoo import models


_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def button_validate(self):
        res = super().button_validate()
        done_outgoing = self.filtered(
            lambda picking: (
                picking.state == "done" and picking.picking_type_id.code == "outgoing"
            )
        )
        if not done_outgoing:
            return res
        sale_orders = done_outgoing.mapped("sale_id")
        if not sale_orders:
            sale_orders = done_outgoing.move_ids.sale_line_id.order_id
        invoices = sale_orders._auto_create_posted_invoices()
        if invoices:
            _logger.info(
                "Automatic delivery invoicing created %s for orders %s",
                ", ".join(invoices.mapped("name")),
                ", ".join(sale_orders.mapped("name")),
            )
        return res
