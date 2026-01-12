# -*- coding: utf-8 -*-
# File: purchase_request_custom/wizard/purchase_request_line_make_purchase_order.py
#
# Odoo 18 – OCA `purchase_request`
# Strictly block creating RFQs/POs over the requested qty **per PR line**.

from odoo import models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare


class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = 'purchase.request.line.make.purchase.order'   # note the dot before "order"

    # ---------------- helpers ----------------
    @staticmethod
    def _first_attr(rec, names, default=None):
        for n in names:
            if hasattr(rec, n):
                return getattr(rec, n)
        return default

    def _uom_convert(self, qty, from_uom, to_uom):
        if not from_uom or not to_uom or from_uom == to_uom:
            return qty
        return from_uom._compute_quantity(qty, to_uom)

    def _remaining_qty_for_line(self, pr_line):
        """
        Remaining = PR requested (PR UoM) - sum(PO lines linked to THIS PR line, not cancelled).
        We **only** consider lines explicitly linked via PR line's `purchase_lines`.
        """
        pr_uom = pr_line.product_uom_id or pr_line.product_id.uom_id
        requested = pr_line.product_qty or 0.0
        taken = 0.0

        # reverse M2M from PR line -> purchase.order.line (standard in OCA module)
        pols = self._first_attr(pr_line, ['purchase_lines', 'purchase_line_ids']) or self.env['purchase.order.line']
        for pol in pols.filtered(lambda l: l.state != 'cancel'):
            pol_uom = self._first_attr(pol, ['product_uom', 'product_uom_id']) or pol.product_id.uom_id
            taken += self._uom_convert(pol.product_qty or 0.0, pol_uom, pr_uom)

        return requested - taken, pr_uom

    def _wizard_items(self):
        """
        Wizard lines container name in OCA is usually `item_ids`
        (model: purchase.request.line.make.purchase.order.item).
        Keep fallbacks just in case.
        """
        return self._first_attr(self, ['item_ids', 'line_ids', 'lines', 'order_line_ids']) or self.env['ir.model.fields']

    # --------------- guard -------------------
    def _guard_block_overqty(self):
        """
        Enforce per-line remaining qty strictly:
          - If remaining <= 0 -> block
          - If intended > remaining -> block
        """
        items = self._wizard_items()
        if not items:
            return

        errors = []

        for it in items:
            pr_line = self._first_attr(it, ['request_line_id', 'purchase_request_line_id', 'pr_line_id', 'line_id'])
            if not pr_line or pr_line._name != 'purchase.request.line':
                continue

            remaining, pr_uom = self._remaining_qty_for_line(pr_line)

            # read intended qty & convert to PR UoM
            qty_field = self._first_attr(it, ['qty_to_order', 'product_qty', 'qty', 'quantity']) or 0.0
            it_uom = self._first_attr(it, ['product_uom_id', 'product_uom']) or pr_uom
            intended = self._uom_convert(qty_field, it_uom, pr_uom)

            rounding = pr_uom.rounding if hasattr(pr_uom, 'rounding') else 0.01

            # fully covered?
            if float_compare(remaining, 0.0, precision_rounding=rounding) <= 0:
                errors.append(
                    _("%(prod)s (PR %(pr)s) is already fully covered. Remaining: 0.00") % {
                        "prod": pr_line.product_id.display_name,
                        "pr": getattr(pr_line, 'request_id', False) and pr_line.request_id.display_name or pr_line.id,
                    }
                )
                continue

            # over-qty in this wizard run?
            if float_compare(intended, remaining, precision_rounding=rounding) > 0:
                errors.append(
                    _("%(prod)s (PR %(pr)s) remaining: %(rem).2f %(uom)s, trying to create: %(intended).2f %(uom)s") % {
                        "prod": pr_line.product_id.display_name,
                        "pr": getattr(pr_line, 'request_id', False) and pr_line.request_id.display_name or pr_line.id,
                        "rem": remaining,
                        "intended": intended,
                        "uom": pr_uom.display_name if hasattr(pr_uom, 'display_name') else '',
                    }
                )

        if errors:
            raise UserError(_("Invalid Operation\n\n%s") % ("\n".join("- " + e for e in errors)))

    # --------------- entry points ---------------
    def make_purchase_order(self):
        self._guard_block_overqty()
        return super().make_purchase_order()

    def action_make_purchase_order(self):
        self._guard_block_overqty()
        try:
            return super().action_make_purchase_order()
        except AttributeError:
            return super().make_purchase_order()
