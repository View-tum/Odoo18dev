# mrp_machine_report_wizard.py
from odoo import models, fields, api, _
from datetime import date
from odoo.exceptions import UserError
import logging
import json

_logger = logging.getLogger(__name__)


class MrpMachineReportWizard(models.TransientModel):
    _name = 'mrp.machine.report.wizard'
    _description = 'Manufacturing Machine Report Wizard'

    # =====================
    # Date Range
    # =====================
    date_from = fields.Date(
        string='Date From',
        required=True,
        default=lambda self: date.today().replace(day=1)
    )
    date_to = fields.Date(
        string='Date To',
        required=True,
        default=lambda self: date.today()
    )

    # =====================
    # Filters
    # =====================
    factory_tag_ids = fields.Many2many(
        'mrp.workcenter.tag',
        string='Factory Type',
        help='Select factory type such as Drug or Plastic'
    )

    machine_ids = fields.Many2many(
        'mrp.workcenter',
        string='Machine',
        help='Select machine(s) to include in the report'
    )

    scrap_filter = fields.Selection(
        [
            ('all', 'All'),
            ('has_scrap', 'Has Scrap'),
            ('no_scrap', 'No Scrap'),
        ],
        string='Scrap Filter',
        default='all'
    )

    include_not_done = fields.Boolean(
        string='Include Not Done Work Orders',
        default=False
    )

    # ---------------------
    # Jasper report selector
    # ---------------------
    report_id = fields.Many2one(
        comodel_name="jasper.report",
        string="Jasper Report",
        required=True,
        domain=[("model_id", "=", "mrp.machine.report.wizard")],
        help="Select jasper report template for this wizard"
    )

    @api.model
    def default_get(self, fields_list):
        res = super(MrpMachineReportWizard, self).default_get(fields_list)
        if "report_id" not in res:
            report = self.env["jasper.report"].search(
                [("model_id", "=", self._name)], limit=1
            )
            if report:
                res["report_id"] = report.id
        return res

    # =====================
    # Actions
    # =====================
    def action_print_report(self):
        """
        Prepare params and call jasper report.
        Uses self.report_id.run_report(docids=[self.id], data=data)
        """
        self.ensure_one()

        if not self.report_id:
            raise UserError(_("Please configure Jasper Report template for this wizard."))

        def csv_or_none(ids):
            """
            Return '1,2,3' or None (no parentheses)
            """
            return ",".join(map(str, ids)) if ids else None

        params = {
            # parameter names must match $P{} in your JRXML
            "date_from": fields.Date.to_string(self.date_from) if self.date_from else None,
            "date_to": fields.Date.to_string(self.date_to) if self.date_to else None,

            # pass as comma-separated strings if JRXML expects that
            "machine_ids_sql": csv_or_none(self.machine_ids.ids),
            "factory_tag_ids_sql": csv_or_none(self.factory_tag_ids.ids),

            "scrap_filter": self.scrap_filter or "all",

            # Postgres CAST($P AS boolean) expects 'true'/'false'
            "include_not_done": "true" if self.include_not_done else "false",
            "printed_by": self.env.user.partner_id.name or self.env.user.name,
        }

        _logger.info("=== JASPER PARAMS ===")
        _logger.info(json.dumps(params, indent=2))

        return self.report_id.run_report(docids=[self.id], data=params)
