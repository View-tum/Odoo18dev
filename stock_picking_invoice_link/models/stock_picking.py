# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import datetime, date

class StockPicking(models.Model):
    _inherit = "stock.picking"

    invoice_ids = fields.Many2many(
        comodel_name="account.move",
        string="Invoices",
        compute="_compute_invoice_ids",
        store=False,
        readonly=True,
    )
    invoice_count = fields.Integer(
        string="Invoice Count",
        compute="_compute_invoice_ids",
        store=False,
    )

    @api.depends(
        "name",
        "state",
        "date_done",
        "scheduled_date",
        "move_ids_without_package.sale_line_id",
        "move_ids_without_package.sale_line_id.order_id.invoice_ids",
        "move_ids_without_package.sale_line_id.order_id.invoice_ids.state",
        "move_ids_without_package.sale_line_id.order_id.invoice_ids.invoice_date",
    )
    def _compute_invoice_ids(self):
        def dt_key(dt):
            return dt or datetime.min

        def d_key(d):
            return d or date.min

        for picking in self:
            # Collect SO(s) from this picking's sale lines
            sale_orders = picking.move_ids_without_package.mapped("sale_line_id").mapped("order_id")
            if not sale_orders:
                picking.invoice_ids = False
                picking.invoice_count = 0
                continue

            # --- 1) Direct link by Ref/Origin containing the picking name ---
            name = picking.name or ""
            invoices = sale_orders.mapped("invoice_ids").filtered(
                lambda m: m.move_type in ("out_invoice", "out_refund") and m.state != "cancel"
            )
            direct = invoices.filtered(
                lambda m: (m.ref and name in m.ref) or (m.invoice_origin and name in m.invoice_origin)
            )
            if direct:
                # Prefer posted, then newest id
                direct = direct.sorted(key=lambda m: (1 if m.state == "posted" else 0, m.id), reverse=True)
                chosen = direct[0]
                picking.invoice_ids = chosen
                picking.invoice_count = 1
                continue

            # --- 2) Pair by sequence within the same SO (no qty usage) ---
            # Use the primary SO (typical case: one SO per picking)
            so = sale_orders[0]

            # Relevant outgoing pickings of the SO (skip cancelled)
            so_pickings = so.picking_ids.filtered(lambda p: p.picking_type_code == "outgoing" and p.state != "cancel")

            # Sort deliveries by done date, then scheduled date, then id
            so_pickings_sorted = sorted(
                so_pickings,
                key=lambda p: (dt_key(p.date_done or p.scheduled_date), p.id),
            )

            # Where is THIS picking in that sequence?
            try:
                idx = so_pickings_sorted.index(picking)
            except ValueError:
                idx = None

            # Sort invoices by invoice date (or accounting date), then id
            so_invoices = so.invoice_ids.filtered(
                lambda m: m.move_type in ("out_invoice", "out_refund") and m.state != "cancel"
            )
            so_invoices_sorted = sorted(
                so_invoices,
                key=lambda m: (d_key(m.invoice_date or m.date), m.id),
            )

            chosen = False
            if idx is not None and idx < len(so_invoices_sorted):
                # Extra safety: ensure the invoice really belongs to this SO via its lines
                candidate = so_invoices_sorted[idx]
                # It already appears in so.invoice_ids because it has at least one line for this SO,
                # so we can accept it.
                chosen = candidate

            picking.invoice_ids = chosen or False
            picking.invoice_count = 1 if chosen else 0

    def action_view_invoices(self):
        self.ensure_one()
        action = self.env.ref("account.action_move_out_invoice_type").sudo().read()[0]
        action["domain"] = [("id", "in", self.invoice_ids.ids)]
        if len(self.invoice_ids) == 1:
            action["views"] = [(self.env.ref("account.view_move_form").id, "form")]
            action["res_id"] = self.invoice_ids.id
        return action
