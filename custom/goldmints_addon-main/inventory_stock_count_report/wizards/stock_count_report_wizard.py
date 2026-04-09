import base64
from werkzeug.urls import url_encode
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from datetime import datetime

from ..services.stock_count_data_service import StockCountDataService
from ..services.stock_count_export_service import StockCountExportService


class StockCountReportWizard(models.TransientModel):
    _name = "inventory.stock.count.report.wizard"
    _description = "Inventory Stock Count Report Wizard"

    location_ids = fields.Many2many(
        "stock.location",
        string="Locations",
        help="Locations to include in the stock count report.",
    )
    include_child_locations = fields.Boolean(
        string="Include Child Locations",
        default=True,
        help="Include child locations of the selected locations.",
    )
    only_on_hand = fields.Boolean(
        string="Only On Hand",
        default=True,
        help="If enabled, only quants with quantity greater than zero are included.",
    )
    mode = fields.Selection(
        [
            ("prefill", "Prefill from system"),
            ("blank", "Blank sheet"),
        ],
        string="Mode",
        default="blank",
        required=True,
    )
    show_uom = fields.Boolean(
        string="Show UoM",
        default=True,
        help="Show the product's unit of measure column.",
    )
    sort_by = fields.Selection(
        [
            ("location", "Location"),
            ("product", "Product"),
            ("lot", "Lot/Serial"),
        ],
        string="Sort By",
        default="location",
        required=True,
    )
    page_break_by_location = fields.Boolean(
        string="Page Break by Location",
        default=True,
        help="Start a new page for each location on the PDF report.",
    )
    show_system_qty = fields.Boolean(
        string="Show System Quantity",
        compute="_compute_show_system_qty",
        help="Automatically set by the selected mode.",
    )
    xlsx_file = fields.Binary(string="File", readonly=True)
    xlsx_filename = fields.Char(string="Filename")

    @api.depends("mode")
    def _compute_show_system_qty(self):
        for wizard in self:
            # Prefill: ไม่แสดง System Qty column
            # Blank: แสดง System Qty เพื่อเทียบตอนนับ
            wizard.show_system_qty = wizard.mode == "blank"

    
    def _report_action(self, report_xmlid, report_type="qweb-pdf"):
        """Return an ir.actions.report with a forced report_type.

        This allows using one report action for:
        - Preview (qweb-html)
        - Print (qweb-pdf)
        """
        self.ensure_one()
        action = self.env.ref(report_xmlid).report_action(self, data={"wizard_id": self.id})
        action["report_type"] = report_type
        return action

    def action_view_html(self):
        self.ensure_one()
        self._ensure_locations_selected()
        return self._report_action(
            "inventory_stock_count_report.stock_count_report_action_pdf",
            report_type="qweb-html",
        )

    def _ensure_locations_selected(self):
        if not self.location_ids:
            raise UserError(_("Please select at least one location."))

    def _get_data_service(self):
        return StockCountDataService(self.env)

    def _get_export_service(self):
        return StockCountExportService(self.env)
    
    def _build_pdf_filename(self):
        timestamp = fields.Datetime.context_timestamp(self, datetime.utcnow())
        return f"stock_count_report_{timestamp.strftime('%Y%m%d_%H%M%S')}.pdf"

    def action_print_pdf(self):
        self.ensure_one()
        self._ensure_locations_selected()

        report_action = self.env.ref(
            "inventory_stock_count_report.stock_count_report_action_pdf"
        )

        # render pdf (ต้องส่ง data wizard_id เหมือนที่ report_action ทำ)
        pdf_content, _ = self.env["ir.actions.report"]._render_qweb_pdf(
            report_action.report_name,
            res_ids=[self.id],
            data={"wizard_id": self.id},
        )

        filename = self._build_pdf_filename()

        att = self.env["ir.attachment"].create(
            {
                "name": filename,
                "type": "binary",
                "datas": base64.b64encode(pdf_content),
                "res_model": self._name,
                "res_id": self.id,
                "mimetype": "application/pdf",
                "public": False,
            }
        )

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{att.id}?download=true",
            "target": "self",
        }

    def action_export_xlsx(self):
        self.ensure_one()
        self._ensure_locations_selected()

        data_service = self._get_data_service()
        lines = data_service.get_lines(self)
        grouped_lines = data_service.group_by_location(lines)

        export_service = self._get_export_service()
        content, filename = export_service.export(
            wizard=self, lines=lines, grouped_lines=grouped_lines
        )

        # Store file on wizard (so /web/content can fetch it)
        self.write(
            {
                "xlsx_file": base64.b64encode(content),
                "xlsx_filename": filename,
            }
        )

        # Direct download (no extra click required)
        query = {
            "model": self._name,
            "id": self.id,
            "field": "xlsx_file",
            "filename_field": "xlsx_filename",
            "download": "true",
        }
        url = "/web/content?%s" % url_encode(query)

        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "self",
        }

    def _get_selected_location_names(self):
        self.ensure_one()
        return ", ".join(self.location_ids.mapped("display_name"))

    def _get_mode_label(self):
        self.ensure_one()
        return dict(self._fields["mode"].selection).get(self.mode)
