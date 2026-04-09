import logging

from odoo import api, models
from odoo.fields import Command
from psycopg2 import IntegrityError

_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.depends("analytic_distribution")
    def _compute_distribution_analytic_account_ids(self):
        # Ensure all records get a value. New/transient records have no DB id yet.
        safe_records = self.exists()
        unsafe_records = self - safe_records
        if unsafe_records:
            unsafe_records.distribution_analytic_account_ids = [Command.clear()]
        if safe_records:
            try:
                with self.env.cr.savepoint():
                    super(
                        AccountMoveLine, safe_records
                    )._compute_distribution_analytic_account_ids()
            except IntegrityError as err:
                if (
                    "account_analytic_account_account_move_line_rel" not in str(err)
                    and "account_analytic_account_account_move" not in str(err)
                ):
                    raise
                # Fallback: compute M2M manually only on records that still exist.
                safe_records = safe_records.exists()
                account_map = {}
                all_account_ids = set()
                for line in safe_records:
                    ids = set()
                    for key in (line.analytic_distribution or {}):
                        for token in str(key).split(","):
                            token = token.strip()
                            if token.isdigit():
                                ids.add(int(token))
                    account_map[line.id] = ids
                    all_account_ids |= ids

                valid_ids = set(
                    self.env["account.analytic.account"]
                    .browse(list(all_account_ids))
                    .exists()
                    .ids
                )
                for line in safe_records.exists():
                    line_ids = list(account_map.get(line.id, set()) & valid_ids)
                    line.distribution_analytic_account_ids = (
                        [Command.set(line_ids)] if line_ids else [Command.clear()]
                    )
                _logger.warning(
                    "Recovered analytic distribution compute after FK violation: %s", err
                )
