# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    manufacturing_date = fields.Datetime(
        related="lot_id.manufacturing_date",
        string="Manufacturing Date",
        store=True,
        readonly=False,
    )

    def _default_lot_manufacturing_dates(self):
        """When a lot is assigned but has no manufacturing date, inherit the picking date."""
        for line in self:
            lot = line.lot_id
            if not lot:
                continue
            # Skip if lot already has a manufacturing date or it's locked
            if lot.manufacturing_date and lot.manufacturing_date_locked:
                _logger.debug("Skipping lot %s because manufacturing_date_locked", lot.id)
                continue
            if lot.manufacturing_date:
                _logger.debug("Skipping lot %s because manufacturing_date already present", lot.id)
                continue
            picking_date = line.picking_id.date or line.picking_id.scheduled_date
            if not picking_date:
                continue
            _logger.info(
                "Auto-setting manufacturing_date for lot %s from move_line %s -> %s (picking %s)",
                lot.id,
                line.id,
                picking_date,
                line.picking_id.id,
            )
            lot.sudo().with_context(lmd_auto_update=True).write({"manufacturing_date": picking_date})

    def _prepare_new_lot_vals(self):
        # Preserve user-provided manufacturing dates when `lot_name` creates a brand new lot on validation.
        vals = super()._prepare_new_lot_vals()
        if self.manufacturing_date:
            vals["manufacturing_date"] = self.manufacturing_date
            vals["manufacturing_date_locked"] = True
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        # If manufacturing_date was provided on creation (manual), lock the related lots
        for vals, rec in zip(vals_list, records):
            if 'manufacturing_date' in vals and not self.env.context.get('lmd_auto_update'):
                lot = rec.lot_id
                if lot:
                    _logger.info("Manual manufacturing_date on create for lot %s (move_line %s); locking", lot.id, rec.id)
                    lot.with_context(lmd_auto_update=True).sudo().write({'manufacturing_date_locked': True})
        records._default_lot_manufacturing_dates()
        return records

    def write(self, vals):
        # Detect manual edits to manufacturing_date on move lines and lock lots when appropriate
        manual_edit = 'manufacturing_date' in vals and not self.env.context.get('lmd_auto_update')
        result = super().write(vals)
        if manual_edit:
            lots = self.mapped('lot_id').filtered(bool)
            if lots:
                _logger.info("Manual manufacturing_date write on move.lines %s -> locking lots %s", self.ids, lots.ids)
                lots.with_context(lmd_auto_update=True).sudo().write({'manufacturing_date_locked': True})
        # Keep default behavior for auto-setting
        self._default_lot_manufacturing_dates()
        return result
