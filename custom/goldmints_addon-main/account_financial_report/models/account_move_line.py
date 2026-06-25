# Copyright 2019 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.fields import Command


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    analytic_account_ids = fields.Many2many(
        "account.analytic.account", compute="_compute_analytic_account_ids", store=True
    )

    @api.constrains("account_id")
    def _check_view_account(self):
        for line in self:
            if line.account_id.is_view:
                raise ValidationError(
                    _("Cannot post transaction to a View/Header account: %s")
                    % line.account_id.display_name
                )

    @api.depends("analytic_distribution")
    def _compute_analytic_account_ids(self):
        safe_records = self.exists()
        unsafe_records = self - safe_records
        if unsafe_records:
            unsafe_records.analytic_account_ids = [Command.clear()]
        if not safe_records:
            return

        all_account_ids = set()
        per_line_ids = {}
        for line in safe_records.filtered("analytic_distribution"):
            parsed_ids = set()
            # ``analytic_distribution`` keys may be "id" or "id,id"
            for key in line.analytic_distribution:
                for token in str(key).split(","):
                    token = token.strip()
                    if token.isdigit():
                        parsed_ids.add(int(token))
            per_line_ids[line.id] = parsed_ids
            all_account_ids |= parsed_ids

        valid_ids = set(
            self.env["account.analytic.account"]
            .browse(list(all_account_ids))
            .exists()
            .ids
        )

        for line in safe_records.exists():
            line_ids = list(per_line_ids.get(line.id, set()) & valid_ids)
            line.analytic_account_ids = (
                [Command.set(line_ids)] if line_ids else [Command.clear()]
            )

    def init(self):
        """
            The join between accounts_partners subquery and account_move_line
            can be heavy to compute on big databases.
            Join sample:
                JOIN
                    account_move_line ml
                        ON ap.account_id = ml.account_id
                        AND ml.date < '2018-12-30'
                        AND ap.partner_id = ml.partner_id
                        AND ap.include_initial_balance = TRUE
            By adding the following index, performances are strongly increased.
        :return:
        """
        self._cr.execute(
            "SELECT indexname FROM pg_indexes WHERE indexname = " "%s",
            ("account_move_line_account_id_partner_id_index",),
        )
        if not self._cr.fetchone():
            self._cr.execute(
                """
            CREATE INDEX account_move_line_account_id_partner_id_index
            ON account_move_line (account_id, partner_id)"""
            )

    @api.model
    def search_count(self, domain, limit=None):
        # In Big DataBase every time you change the domain widget this method
        # takes a lot of time. This improves performance
        if self.env.context.get("skip_search_count"):
            return 0
        return super().search_count(domain, limit=limit)
