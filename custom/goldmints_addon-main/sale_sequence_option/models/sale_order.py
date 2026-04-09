from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    sequence_option = fields.Boolean(default=False, copy=False, index=True)

    def action_confirm(self):
        options = self.env["ir.sequence.option.line"].get_model_options(self._name)
        if options:
            for order in self:
                if order.sequence_option:
                    continue
                sequence = self.env["ir.sequence.option.line"].get_sequence(order, options=options)
                if sequence:
                    # Use context_today as confirmation date, as date_order is updated in super()
                    seq_date = fields.Date.context_today(order)
                    order.name = sequence.next_by_id(sequence_date=seq_date)
                    order.sequence_option = True
        return super().action_confirm()
