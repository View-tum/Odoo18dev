from odoo import api, fields, models


class ContractRebateSummary(models.Model):
    _name = "contract.rebate.summary"
    _description = "Contract Monthly Sales Summary"
    _order = "month desc"

    contract_id = fields.Many2one(
        "contract.document",
        string="Contract",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        related="contract_id.company_id",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="contract_id.currency_id",
        store=True,
        readonly=True,
    )
    month = fields.Date(string="Month Date", required=True)
    month_display = fields.Char(
        string="Month",
        compute="_compute_month_display",
        store=True,
    )
    sales_amount = fields.Monetary(
        string="Sales",
        currency_field="currency_id",
    )
    ytd_amount = fields.Monetary(
        string="Check Vol.",
        currency_field="currency_id",
        help="Year-to-date cumulative sales",
    )
    rate = fields.Float(
        string="Rate",
        digits=(16, 2),
    )
    est_rebate = fields.Monetary(
        string="Est. Rebate",
        currency_field="currency_id",
        compute="_compute_est_rebate",
        store=True,
    )
    state = fields.Selection(
        [
            ("pending", "Pending"),
            ("met", "Met"),
        ],
        string="Status",
        compute="_compute_state",
        store=True,
    )

    @api.depends("month")
    def _compute_month_display(self):
        for rec in self:
            if rec.month:
                rec.month_display = rec.month.strftime("%m/%Y")
            else:
                rec.month_display = ""

    @api.depends("sales_amount", "ytd_amount", "contract_id.rebate_period", "contract_id.rebate_tier_ids", "contract_id.rebate_rate")
    def _compute_est_rebate(self):
        for rec in self:
            contract = rec.contract_id
            check_val = rec.sales_amount if contract.rebate_period == 'monthly' else rec.ytd_amount
            
            applied_rate = contract.rebate_rate or 0.0
            fixed_payout = 0.0
            if contract.rebate_tier_ids:
                matching_tier = contract.rebate_tier_ids.sorted('min_amount', reverse=True).filtered(
                    lambda t: check_val >= t.min_amount
                )[:1]
                if matching_tier:
                    if matching_tier.fixed_amount > 0:
                        fixed_payout = matching_tier.fixed_amount
                        applied_rate = 0.0
                    else:
                        applied_rate = matching_tier.rebate_rate
                else:
                    applied_rate = 0.0

            if fixed_payout > 0:
                rec.est_rebate = fixed_payout
            else:
                rec.est_rebate = rec.sales_amount * (applied_rate / 100.0)



    @api.depends("sales_amount", "ytd_amount", "contract_id.rebate_period", "contract_id.rebate_tier_ids", "contract_id.rebate_rate")
    def _compute_state(self):
        for rec in self:
            contract = rec.contract_id
            check_val = rec.sales_amount if contract.rebate_period == 'monthly' else rec.ytd_amount
            
            is_met = False
            if contract.rebate_tier_ids:
                # Check if it reached any tier with rate > 0
                matching_tier = contract.rebate_tier_ids.sorted('min_amount', reverse=True).filtered(
                    lambda t: check_val >= t.min_amount and t.rebate_rate > 0
                )[:1]
                is_met = bool(matching_tier)
            elif contract.rebate_rate > 0:
                is_met = check_val >= contract.rebate_target_amount

            rec.state = "met" if is_met else "pending"



class ContractRebateHistory(models.Model):
    _name = "contract.rebate.history"
    _description = "Contract Rebate Payment History"
    _order = "date desc"

    contract_id = fields.Many2one(
        "contract.document",
        string="Contract",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        related="contract_id.company_id",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="contract_id.currency_id",
        store=True,
        readonly=True,
    )
    date = fields.Date(string="Date", required=True, default=fields.Date.today)
    move_id = fields.Many2one(
        "account.move",
        string="Vendor Bill",
        domain=[("move_type", "=", "in_invoice")],
    )
    amount = fields.Monetary(
        string="Amount",
        currency_field="currency_id",
    )
    note = fields.Text(string="Note")


class ContractRebateTier(models.Model):
    _name = "contract.rebate.tier"
    _description = "Contract Rebate Tier"
    _order = "min_amount desc"

    contract_id = fields.Many2one(
        "contract.document",
        string="Contract",
        required=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(
        "res.company",
        related="contract_id.company_id",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="contract_id.currency_id",
        store=True,
        readonly=True,
    )
    min_amount = fields.Monetary(
        string="Min Sales Amount",
        currency_field="currency_id",
        required=True,
        help="Minimum sales required to reach this tier.",
    )
    rebate_rate = fields.Float(
        string="Rebate Rate (%)",
        digits=(16, 2),
        required=True,
        default=0.0,
        help="Percentage of sales to pay back as rebate for this tier.",
    )
    fixed_amount = fields.Monetary(
        string="Fixed Amount",
        currency_field="currency_id",
        default=0.0,
        help="Fixed amount to pay back as rebate for this tier (if not using percentage).",
    )


