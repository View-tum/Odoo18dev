from datetime import datetime

from odoo import fields, models

from ..services.stock_count_data_service import StockCountDataService


class StockCountReport(models.AbstractModel):
    _name = "report.inventory_stock_count_report.stock_count_report_template"
    _description = "Inventory Stock Count Report PDF"

    def _get_data_service(self):
        return StockCountDataService(self.env)

    def _prepare_report_data(self, wizard):
        wizard._ensure_locations_selected()
        data_service = self._get_data_service()
        lines = data_service.get_lines(wizard)
        grouped_lines = data_service.group_by_location(lines)
        return {
            "wizard": wizard,
            "lines": lines,
            "grouped_lines": grouped_lines,
            "show_system_qty": wizard.show_system_qty,
            "show_uom": wizard.show_uom,
            "page_break_by_location": wizard.page_break_by_location,
            "selected_locations": wizard._get_selected_location_names(),
            "mode_label": wizard._get_mode_label(),
            "company": wizard.env.company,
            "printed_at": fields.Datetime.context_timestamp(wizard, datetime.utcnow()),
        }

    def _get_report_values(self, docids, data=None):
        data = data or {}

        wizard_id = data.get("wizard_id")
        if wizard_id:
            wizard = self.env["inventory.stock.count.report.wizard"].browse(wizard_id).exists()
        else:
            wizard = self.env["inventory.stock.count.report.wizard"].browse(docids).exists()

        if not wizard:
            return {}
        wizard.ensure_one()
        report_data = self._prepare_report_data(wizard)
        return {
            "doc_ids": wizard.ids,
            "doc_model": wizard._name,
            "docs": wizard,
            "data": report_data,
        }
