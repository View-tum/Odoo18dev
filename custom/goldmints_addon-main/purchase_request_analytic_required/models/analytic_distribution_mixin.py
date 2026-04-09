# -*- coding: utf-8 -*-
import json

from odoo import _, models
from odoo.exceptions import ValidationError


class AnalyticDistributionCheckMixin(models.AbstractModel):
    _name = "analytic.distribution.check.mixin"
    _description = "Analytic Distribution validation helper"

    def _analytic_distribution_total(self):
        """Return the total percentage stored on the analytic distribution."""
        self.ensure_one()
        distribution = self.analytic_distribution
        if not distribution:
            return 0.0
        if isinstance(distribution, str):
            try:
                distribution = json.loads(distribution)
            except Exception as err:
                raise ValidationError(
                    _(
                        "Analytic distribution JSON is invalid on line %(line)s: %(error)s"
                    )
                    % {"line": self.display_name, "error": err}
                )
        if isinstance(distribution, dict):
            total = 0.0
            for value in distribution.values():
                if isinstance(value, dict):
                    total += float(
                        value.get("percentage", value.get("percent", value.get("value", 0.0)))
                    )
                else:
                    total += float(value or 0.0)
            return total
        if isinstance(distribution, list):
            total = 0.0
            for item in distribution:
                if isinstance(item, dict):
                    total += float(
                        item.get("percentage", item.get("percent", item.get("value", 0.0)))
                    )
                else:
                    total += float(item or 0.0)
            return total
        raise ValidationError(
            _("Unsupported analytic distribution format on line %s.") % self.display_name
        )
