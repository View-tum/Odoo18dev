from odoo import models, fields, api


class SaleAnalysisReportConfig(models.Model):
    _name = "sale.analysis.report.config"
    _description = "Sale Analysis Report Configuration"
    _rec_name = "filter_by"

    filter_by = fields.Selection(
        selection=[
            ("salesperson", "Salesperson"),
            ("product", "Product"),
            ("market_region", "Sales Zone"),
            ("top_ten", "Top 10 Best-Selling Products"),
        ],
        string="Filter by",
        required=True,
        help="(365 custom) Select the criteria to map with the report template.",
    )

    report_id = fields.Many2one(
        comodel_name="jasper.report",
        string="Report Template",
        required=True,
        domain=[("model_id.model", "=", "sale.analysis.report")],
        help="(365 custom) Select the Jasper Report template to be automatically selected.",
    )

    _sql_constraints = [
        (
            "filter_by_uniq",
            "unique(filter_by)",
            "This filter criteria is already configured!",
        )
    ]
