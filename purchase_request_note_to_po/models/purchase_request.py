# -*- coding: utf-8 -*-
from markupsafe import escape
from odoo import api, models


class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = 'purchase.request.line.make.purchase.order'

    @api.model
    def _prepare_purchase_order(self, *args, **kwargs):
        purchase_vals = super()._prepare_purchase_order(*args, **kwargs)
        pr_descriptions = self._collect_pr_descriptions()
        if pr_descriptions:
            notes_addition = self._format_descriptions_html(pr_descriptions)
            existing_notes = purchase_vals.get('notes') or ''
            purchase_vals['notes'] = (
                f"{existing_notes}{notes_addition}" if existing_notes else notes_addition
            )
        return purchase_vals

    def _collect_pr_descriptions(self):
        seen = set()
        descriptions = []
        requests = self.item_ids.mapped('request_id') or self.item_ids.mapped('line_id.request_id')
        for request in requests:
            desc = (request.description or '').strip()
            if desc and desc not in seen:
                seen.add(desc)
                descriptions.append(desc)
        return descriptions

    @staticmethod
    def _format_descriptions_html(descriptions):
        paragraphs = []
        for description in descriptions:
            escaped = escape(description)
            escaped_str = '<br/>'.join(str(escaped).splitlines())
            paragraphs.append(f"<p>{escaped_str}</p>")
        return ''.join(paragraphs)
