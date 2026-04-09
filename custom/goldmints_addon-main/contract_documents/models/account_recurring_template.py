from dateutil.relativedelta import relativedelta
from odoo import api, fields, models


class AccountRecurringTemplate(models.Model):
    _inherit = "account.recurring.template"

    contract_id = fields.Many2one(
        "contract.document",
        string="Linked Contract",
        readonly=False,
        help="The contract document this rebate payment is based on.",
    )

    @api.onchange("partner_id", "computing_mode")
    def _onchange_partner_id_fetch_rebate(self):
        """Override to also populate contract_id link"""
        res = super()._onchange_partner_id_fetch_rebate()
        if self.computing_mode == "rebate" and self.partner_id:
            Contract = self.env.get("contract.document")
            if Contract is not None:
                contract = Contract.search(
                    [
                        (
                            "partner_id",
                            "child_of",
                            self.partner_id.commercial_partner_id.id,
                        ),
                        ("state", "=", "open"),
                    ],
                    limit=1,
                    order="date_end desc",
                )
                if contract:
                    self.contract_id = contract.id
                    # Match Scheduling & Dates
                    self.start_date = contract.date_start
                    self.end_date = contract.date_end
                    self.recurring_period = "months"
                    self.recurring_interval = 1
                else:
                    self.contract_id = False
        else:
            self.contract_id = False
        return res

    def _rebate_notification_hook(self, date_from, month_sales):
        """Notify salesperson in the 11th month if yearly target is at risk"""
        super()._rebate_notification_hook(date_from, month_sales)
        if self.rebate_type != "yearly" or self.rebate_target_amount <= 0:
            return

        # Check if it's the month before contract end
        is_warning_month = False
        if self.contract_id and self.contract_id.date_end:
            # Logic: warning month is EXACTLY 1 month before contract end month
            warning_month_date = self.contract_id.date_end - relativedelta(months=1)
            if (
                date_from.month == warning_month_date.month
                and date_from.year == warning_month_date.year
            ):
                is_warning_month = True
        elif not self.contract_id and date_from.month == 11:
            # Default to Nov for calendar year if no contract
            is_warning_month = True

        if is_warning_month:
            # Calculate YTD sales including this month
            ytd_start = date_from.replace(month=1, day=1)
            if (
                self.contract_id
                and self.contract_id.date_start.year == date_from.year
                and self.contract_id.date_start > ytd_start
            ):
                ytd_start = self.contract_id.date_start

            ytd_domain = [
                ("move_type", "=", "out_invoice"),
                ("state", "=", "posted"),
                ("partner_id", "child_of", self.partner_id.commercial_partner_id.id),
                ("invoice_date", ">=", ytd_start),
                (
                    "invoice_date",
                    "<=",
                    date_from.replace(day=1)
                    + relativedelta(months=1)
                    - relativedelta(days=1),
                ),
                ("company_id", "=", self.company_id.id),
            ]
            ytd_sales = sum(
                self.env["account.move"].search(ytd_domain).mapped("amount_untaxed")
            )

            if ytd_sales < self.rebate_target_amount:
                diff = self.rebate_target_amount - ytd_sales
                responsible = (
                    self.contract_id.user_id
                    if self.contract_id
                    else self.partner_id.user_id
                )

                if responsible:
                    # DEDUPLICATION: Check if an activity for this target warning already exists
                    existing = self.env["mail.activity"].search(
                        [
                            ("res_id", "=", self.id),
                            (
                                "res_model_id",
                                "=",
                                self.env["ir.model"]._get_id(self._name),
                            ),
                            ("summary", "ilike", "แจ้งเตือนเป้า Rebate"),
                            ("date_deadline", ">=", date_from.replace(day=1)),
                            ("state", "!=", "done"),
                        ],
                        limit=1,
                    )

                    if existing:
                        return

                    msg = (
                        f"⚠️ **แจ้งเตือนเป้าหมาย Rebate รายปี**\n\n"
                        f"ขณะนี้ยอดขายของลูกค้า **{self.partner_id.name}** อยู่ที่ **{ytd_sales:,.2f}** บาท\n"
                        f"ยังขาดอีก **{diff:,.2f}** บาท จะถึงเป้ารายปี (**{self.rebate_target_amount:,.2f}**) ครับ\n\n"
                        f"หากทำยอดไม่ถึง ลูกค้าจะไม่ได้รับเงินคืนทั้งหมดที่สำรองจ่ายไป 11 เดือนที่ผ่านมาครับ"
                    )
                    target_record = self.contract_id or self.partner_id
                    if target_record:
                        target_record.activity_schedule(
                            "mail.mail_activity_data_todo",
                            summary=f"แจ้งเตือนเป้า Rebate: {self.partner_id.name}",
                            note=msg,
                            user_id=responsible.id,
                        )

    def _calculate_rebate_amount(self, target_date):
        self.ensure_one()
        if self.computing_mode != "rebate":
            return super()._calculate_rebate_amount(target_date)

        if not self.contract_id:
            return 0.0

        contract = self.contract_id
        
        # Adjust dates based on period
        date_to = target_date
        if contract.rebate_period == 'monthly':
            date_from = target_date.replace(day=1)
        elif contract.rebate_period == 'quarterly':
            # End of previous quarter logic
            month = target_date.month
            quarter_start_month = ((month - 1) // 3) * 3 + 1
            date_from = target_date.replace(month=quarter_start_month, day=1)
            # Only process on the last month of the quarter (3, 6, 9, 12)
            if month % 3 != 0:
                return 0.0
        else: # Yearly
            date_from = target_date.replace(month=1, day=1)

        # Sales Aggregation
        if contract.rebate_target_type == 'group':
            partners = contract.rebate_group_id.partner_ids.mapped('commercial_partner_id')
        else:
            partners = contract.partner_id.commercial_partner_id

        if not partners:
            return 0.0

        invoices = self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('partner_id', 'child_of', partners.ids),
            ('invoice_date', '>=', date_from),
            ('invoice_date', '<=', date_to),
            ('company_id', '=', self.company_id.id),
        ])
        total_sales = sum(invoices.mapped('amount_untaxed'))

        # Tier Matching (Flat)
        applied_rate = contract.rebate_rate or 0.0
        fixed_payout = 0.0
        if contract.rebate_tier_ids:
            matching_tier = contract.rebate_tier_ids.sorted('min_amount', reverse=True).filtered(
                lambda t: total_sales >= t.min_amount
            )[:1]
            if matching_tier:
                if matching_tier.fixed_amount > 0:
                    fixed_payout = matching_tier.fixed_amount
                    applied_rate = 0.0
                else:
                    applied_rate = matching_tier.rebate_rate
            else:
                applied_rate = 0.0 # Didn't reach first tier

        if fixed_payout > 0:
            return fixed_payout
        return total_sales * (applied_rate / 100.0)


