# -*- coding: utf-8 -*-
import logging

from odoo import fields, models
from datetime import timedelta

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def button_validate(self):
        _logger.debug("button_validate called on pickings %s by user %s", self.ids, self.env.user.id)
        res = super().button_validate()
        # After validation, auto-fill manufacturing dates for incoming pickings
        self._lmd_auto_set_manufacturing_dates()
        return res

    def _lmd_auto_set_manufacturing_dates(self):
        """Populate lot manufacturing dates when left empty on Receipts."""
        for picking in self.filtered(lambda p: p.picking_type_id.code == "incoming"):
            date = picking.date_done or fields.Datetime.now()
            _logger.debug("Auto-set manufacturing_date for picking %s using date %s", picking.id, date)
            lots = picking.move_line_ids.filtered(
                lambda ml: ml.lot_id
                and not ml.lot_id.manufacturing_date
                and not ml.lot_id.manufacturing_date_locked
            ).mapped("lot_id")
            if not lots:
                continue
            # Protect recent manual edits: skip lots that were written very recently
            now = fields.Datetime.now()
            def _is_recent(lot, now=now):
                if not lot.write_date:
                    return False
                try:
                    delta = fields.Datetime.to_datetime(now) - fields.Datetime.to_datetime(lot.write_date)
                    return delta.total_seconds() <= 120
                except Exception:
                    return False
            safe_lots = lots.filtered(lambda l, _is_recent=_is_recent: not _is_recent(l))
            if not safe_lots:
                _logger.info("Skipping auto-set for lots %s on picking %s because they were modified recently", lots.ids, picking.id)
                continue
            _logger.info("Will auto-set manufacturing_date for lots %s on picking %s -> %s", safe_lots.ids, picking.id, date)
            safe_lots.with_context(lmd_auto_update=True).write({"manufacturing_date": date})
