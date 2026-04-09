from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    petty_cash_journal_id = fields.Many2one(
        "account.journal",
        string="Default Petty Cash Journal",
        domain=[("type", "=", "cash")],
    )
    petty_cash_analytic_distribution = fields.Json(
        string="Default Analytic Distribution"
    )

    analytic_precision = fields.Integer(
        store=False,
        default=lambda self: self.env["decimal.precision"].precision_get(
            "Percentage Analytic"
        ),
    )


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    petty_cash_journal_id = fields.Many2one(
        related="company_id.petty_cash_journal_id",
        string="Default Petty Cash Journal",
        readonly=False,
    )
    petty_cash_analytic_distribution = fields.Json(
        related="company_id.petty_cash_analytic_distribution",
        string="Default Analytic Distribution",
        readonly=False,
    )

    analytic_precision = fields.Integer(
        related="company_id.analytic_precision",
        readonly=False,
    )
