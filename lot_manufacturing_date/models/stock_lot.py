# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class StockLot(models.Model):
    _inherit = 'stock.lot'

    manufacturing_date = fields.Datetime(
        string="Manufacturing Date",
        help="The date on which the goods with this Serial Number were manufactured.",
    )
    manufacturing_date_locked = fields.Boolean(
        string="Manufacturing Date Locked",
        help="Set to True once a user manually edits the Manufacturing Date so automatic updates do not overwrite it.",
        default=False,
    )

    def write(self, vals):
        manual_change = False
        if 'manufacturing_date' in vals and not self.env.context.get('lmd_auto_update'):
            manual_change = True
        _logger.debug("StockLot.write called for %s, vals=%s, ctx_lmd_auto=%s, user=%s", self._name, vals, bool(self.env.context.get('lmd_auto_update')), self.env.user.id)
        res = super().write(vals)
        if manual_change:
            to_lock = self.filtered(lambda lot: bool(lot.manufacturing_date))
            to_unlock = self - to_lock
            if to_lock:
                _logger.info(
                    "Locking manufacturing_date for lots %s (manual change)",
                    to_lock.ids,
                )
                to_lock.with_context(lmd_auto_update=True).sudo().write({'manufacturing_date_locked': True})
            if to_unlock:
                _logger.info(
                    "Unlocking manufacturing_date for lots %s (no manufacturing_date present)",
                    to_unlock.ids,
                )
                to_unlock.with_context(lmd_auto_update=True).sudo().write({'manufacturing_date_locked': False})
        return res
