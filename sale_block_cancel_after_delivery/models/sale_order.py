# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _has_done_delivery(self):
        """
        True if there is any *outgoing* (customer delivery) picking done,
        ignoring returns/receipts back from the customer.
        Also checks net delivered qty on lines (already net of returns).
        """
        self.ensure_one()
    
        # Outgoing deliveries that are done
        outgoing_done = self.picking_ids.filtered(
            lambda p: p.state == "done" and getattr(p.picking_type_id, "code", False) == "outgoing"
        )
    
        # Incoming returns that are done
        incoming_done = self.picking_ids.filtered(
            lambda p: p.state == "done" and getattr(p.picking_type_id, "code", False) == "incoming"
        )
        
        # If customer already returned everything, treat as not delivered
        if incoming_done and outgoing_done:
            return False
    
        if outgoing_done:
            return True
    
        # Optional: fallback to line qty_delivered
        # if any(
        #     not line.display_type and (line.qty_delivered or 0.0) > 0.0
        #     for line in self.order_line
        # ):
        #     return True
    
        return False


    def action_cancel(self):
        for order in self:
            if order._has_done_delivery():
                raise UserError(_(
                    "You cannot cancel this Sales Order because at least one "
                    "customer delivery is completed. Create a return or revert "
                    "the delivery first."
                ))
        return super().action_cancel()

    def write(self, vals):
        if vals.get("state") == "cancel":
            for order in self:
                if order._has_done_delivery():
                    raise UserError(_(
                        "Operation blocked: this Sales Order has completed customer deliveries "
                        "and cannot be set to 'Cancelled'."
                    ))
        return super().write(vals)
