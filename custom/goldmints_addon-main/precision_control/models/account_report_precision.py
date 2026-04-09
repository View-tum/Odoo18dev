from odoo import models
from odoo.tools.misc import formatLang


class AccountReportPrecision(models.Model):
    _inherit = "account.report"

    def _get_precision_control_account_digits(self):
        value = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("precision_control.precision_account", default="2")
        )
        try:
            return int(value)
        except (TypeError, ValueError):
            return 2

    def _format_value(self, options, value, figure_type, format_params=None):
        result = super()._format_value(
            options=options,
            value=value,
            figure_type=figure_type,
            format_params=format_params,
        )

        if figure_type != "monetary" or value is None or self._context.get("no_format"):
            return result

        # Preserve default formatting for multi-currency reports.
        if options.get("multi_currency"):
            return result

        digits = self._get_precision_control_account_digits()
        fmt_options = {
            "rounding_method": "HALF-UP",
            "rounding_unit": options.get("rounding_unit"),
            "digits": digits,
        }
        if self._is_value_zero(value, figure_type, format_params or {}):
            value = abs(value)
        return formatLang(self.env, value, **fmt_options)
