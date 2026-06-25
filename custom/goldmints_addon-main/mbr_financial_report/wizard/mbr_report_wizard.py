from datetime import date, datetime, timedelta
import calendar
import re
from calendar import month_name

from odoo import api, fields, models, _


class MBRReportWizard(models.TransientModel):
    _name = "mbr.report.wizard"
    _description = "MBR Report Wizard"

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    year = fields.Selection(
        selection=lambda self: self._year_selection(),
        string="Year",
        required=True,
        default=lambda self: str(date.today().year),
    )
    period_type = fields.Selection(
        [("month", "Month"), ("quarter", "Quarter")],
        string="Period Type",
        required=True,
        default="month",
    )
    quarter = fields.Selection(
        [("1", "Q1"), ("2", "Q2"), ("3", "Q3"), ("4", "Q4")],
        string="Quarter",
        default=lambda self: str((date.today().month - 1) // 3 + 1),
    )
    month = fields.Selection(
        [(str(i), month_name[i]) for i in range(1, 13)],
        string="Month",
        required=True,
        default=lambda self: str(date.today().month),
    )
    date_from = fields.Date(
        string="Date From",
        required=True,
        default=lambda self: date.today().replace(day=1),
    )
    date_to = fields.Date(
        string="Date To",
        required=True,
        default=lambda self: (date.today().replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1),
    )
    target_move = fields.Selection(
        [("posted", "Posted"), ("all", "All")],
        string="Target Moves",
        default="all",
        required=True,
    )
    compare = fields.Boolean(string="Add Comparison")
    compare_date_from = fields.Date(string="Comparison Date From")
    compare_date_to = fields.Date(string="Comparison Date To")
    journal_ids = fields.Many2many(
        "account.journal",
        string="Journals",
        domain="[('company_id', '=', company_id)]",
    )
    scale = fields.Integer(
        string="Scale (divider)",
        required=True,
        default=1,
        help="Numbers will be divided by this value (use 1 for exact amounts).",
    )

    # Line definitions: mapping to pseudo 'Excel source rows'
    LINE_DEFS = [
        # 1. Revenue
        {"code": "1.1.1", "name": "Domestic Sales", "src_row": 61, "section": "revenue"},
        {"code": "1.1.2", "name": "International Sales", "src_row": 62, "section": "revenue"},
        {"code": "1.2", "name": "Services", "src_row": 7, "section": "revenue"},
        {"code": "1.3", "name": "Rental", "src_row": 8, "section": "revenue"},
        {"code": "1.4", "name": "Other income", "src_row": 9, "section": "revenue"},
        # 2. Cost of Sales / Services
        {"code": "2.1.1", "name": "Cost of Sales - Domestic", "src_row": 13, "section": "cogs"},
        {"code": "2.1.2", "name": "Cost of Sales - International", "src_row": 14, "section": "cogs"},
        {"code": "2.3", "name": "Cost of Rental", "src_row": 15, "section": "cogs"},
        {"code": "2.4", "name": "Other expenses", "src_row": 16, "section": "cogs"},
        # 3. Operating expenses
        {"code": "3.1", "name": "Salary and Benefit and Other", "src_row": 22, "section": "opex"},
        {"code": "3.2", "name": "Management / Technical Service fee", "src_row": 23, "section": "opex"},
        {"code": "3.3", "name": "Rental expenses", "src_row": 24, "section": "opex"},
        {"code": "3.4", "name": "Utilities", "src_row": 25, "section": "opex"},
        {"code": "3.5", "name": "Travelling and Accommodation", "src_row": 26, "section": "opex"},
        {"code": "3.6", "name": "Commission and Marketing", "src_row": 27, "section": "opex"},
        {"code": "3.7", "name": "Training", "src_row": 28, "section": "opex"},
        {"code": "3.8", "name": "Tax and government fee", "src_row": 29, "section": "opex"},
        {"code": "3.9", "name": "Consulting fees", "src_row": 30, "section": "opex"},
        {"code": "3.10", "name": "Repair and maintenance", "src_row": 31, "section": "opex"},
        {"code": "3.11", "name": "Depreciations", "src_row": 32, "section": "opex"},
        {"code": "3.12", "name": "Transportation expenses", "src_row": 33, "section": "opex"},
        {"code": "3.13", "name": "Other expenses", "src_row": 34, "section": "opex"},
        {"code": "3.14", "name": "(Gain) / Loss on Exchange Rate", "src_row": 35, "section": "opex"},
        # 4. Financial costs
        {"code": "4.1", "name": "Interest", "src_row": 41, "section": "finance"},
        {"code": "4.2", "name": "Other financial costs", "src_row": 42, "section": "finance"},
    ]

    def action_print_pdf(self):
        self.ensure_one()
        return self.env.ref(
            "mbr_financial_report.action_report_mbr"
        ).report_action(self)

    def action_export_xlsx(self):
        self.ensure_one()
        # Use the HTML preview; template will offer XLSX download
        ctx = dict(self.env.context)
        if self.period_type == "quarter" and self.quarter and self.year:
            period_str = f"Q{self.quarter} {self.year}"
        else:
            month_name_str = date(int(self.year), int(self.month), 1).strftime("%B") if self.year and self.month else "MBR"
            period_str = f"{month_name_str} {self.year}" if self.year else month_name_str
        ctx["report_file"] = f"{period_str} MBR"
        return self.env.ref("mbr_financial_report.action_report_mbr_html").with_context(ctx).report_action(self)

    def action_auto_map_coa(self):
        """Auto-create mbr.account.map rows from the current COA."""
        self.ensure_one()
        AccountMap = self.env["mbr.account.map"]
        Account = self.env["account.account"]

        # Wipe existing mappings for this company to avoid duplicates.
        AccountMap.search([("company_id", "=", self.company_id.id)]).unlink()

        # Code-based mapping supplied by user
        def normalize(code):
            return (code or "").strip()

        lines_map = {
            "1.1.1": {
                "410001", "410002", "410003", "410004", "410088",
            },
            "1.1.2": {
                "420001", "420002",
            },
            "1.2": {
                "420006", "420007", "430001",
            },
            "1.3": set(),
            "1.4": {
                "470003", "470004", "470005", "420003", "470006", "470007",
                "470008", "420004", "480001",
            },
            "2.1.1": {
                "510001", "510002", "510003", "510004", "520100",
            },
            "2.1.2": {
                "520001", "520002", "520004", "520005",
            },
            "2.3": {
                "540014",
            },
            "2.4": {
                "590001", "590002", "590003", "590004", "590005", "590006",
                "522008", "530001", "530002", "530005", "530006", "530007",
                "530008", "530009", "530004", "540001", "540003", "540004",
                "540005", "540006", "540002", "610312", "540007", "540008",
                "550029", "550058", "540010", "522001", "522002", "522005",
                "540011", "550008", "550014", "550034", "540012", "621302",
            },
            "3.1": {
                "620101", "620102", "620103", "620104", "620105", "620106",
                "620107", "620108", "620109", "620110", "620111", "620113",
                "620114", "620115", "620116", "621109",
            },
            "3.2": {"620815"},
            "3.3": {"620501", "620502", "620503", "620504", "620506", "620508"},
            "3.4": {"620201", "620202", "620301", "620302", "620303"},
            "3.5": {
                "620601", "620602", "620603", "620604", "620605", "620606", "621108",
            },
            "3.6": {
                "610301", "610302", "610303", "610304", "610305", "610306",
                "610307", "610308", "610309", "610310", "610313", "610314",
                "610315", "610316", "610317", "621314", "610320",
            },
            "3.7": {"620112", "620813"},
            "3.8": {"620905", "620906"},
            "3.9": {"620701", "620702", "620703", "620704"},
            "3.10": {
                "621001", "621002", "621003", "621004", "621005", "621006",
                "621110", "621111", "621112", "621101", "550035", "621113",
                "621501",
            },
            "3.11": {
                "621201", "621202", "621203", "621204", "621205", "621206",
                "621207", "621208", "621209", "621210", "621211", "621212",
                "621213", "621214", "621215",
            },
            "3.12": {"610311", "550025"},
            "3.13": {
                "620401", "610304", "620402", "620403", "620404", "620405",
                "620406", "620408", "620802", "620801", "620803", "620814",
                "620903", "621301", "621303", "621304", "621305", "621306",
                "620505", "621307", "621308", "621309", "621312", "621310",
                "621311", "621315", "620304", "620305", "710002",
            },
            "3.14": {"470001", "470002"},
            "4.1": {"621402", "621405", "621404"},
            "4.2": {"621401", "621403", "620901", "620904"},
        }

        code_to_line = {}
        for line_code, codes in lines_map.items():
            for c in codes:
                code_to_line[normalize(c)] = line_code

        def guess_line(acc):
            code = normalize(getattr(acc, "code", ""))
            return code_to_line.get(code, False)

        accounts = Account.search([("company_ids", "in", self.company_id.id)])
        created = 0
        skipped = 0
        for acc in accounts:
            target = guess_line(acc)
            if not target:
                skipped += 1
                continue
            AccountMap.create(
                {
                    "company_id": self.company_id.id,
                    "account_id": acc.id,
                    "line_code": target,
                }
            )
            created += 1

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("MBR Mapping"),
                "message": _("Created %s mappings, skipped %s (no rule).") % (created, skipped),
                "type": "success",
                "sticky": False,
            },
        }

    def _period_labels(self, date_from, date_to):
        df = fields.Date.to_date(date_from)
        dt = fields.Date.to_date(date_to)
        current_label = _("Current Period - %s to %s") % (
            df.strftime("%d %b %Y"),
            dt.strftime("%d %b %Y"),
        )
        ytd_label = _("YTD %s (Jan - %s)") % (dt.year, dt.strftime("%b"))
        period_label = _("For The Period %s to %s") % (
            df.strftime("%d %b %Y"),
            dt.strftime("%d %b %Y"),
        )
        return current_label, ytd_label, period_label

    @classmethod
    def _line_code_to_src_row(cls):
        return {ld["code"]: ld["src_row"] for ld in cls.LINE_DEFS}

    @staticmethod
    def _choose_month(values_by_month, month_idx):
        if not values_by_month or not (1 <= month_idx <= 12):
            return 0.0
        return float(values_by_month[month_idx - 1])

    @staticmethod
    def _safe_div(num, den):
        return num / den if den else 0.0

    @staticmethod
    def _month_from_key(month_key):
        """Handle various date:month groupby return shapes."""
        if not month_key:
            return None
        # date/datetime objects
        if hasattr(month_key, "month"):
            try:
                return int(month_key.month)
            except Exception:
                return None
        # integer month
        if isinstance(month_key, int) and 1 <= month_key <= 12:
            return month_key
        if isinstance(month_key, str):
            s = month_key.strip()
            # ISO-ish: YYYY-MM or YYYY-MM-DD or YYYYMM
            m = re.match(r"^\\d{4}-(\\d{2})(?:-\\d{2})?$", s)
            if m:
                return int(m.group(1))
            m = re.match(r"^(\\d{4})(\\d{2})$", s)
            if m:
                return int(m.group(2))
            for fmt in ("%B %Y", "%b %Y", "%Y-%m", "%Y-%m-%d"):
                try:
                    return datetime.strptime(s, fmt).month
                except Exception:
                    continue
        return None

    # ---------------- ACTUAL DATA -----------------

    def _get_actual_matrix(self, date_from, date_to):
        self.ensure_one()
        line_code_to_src = self._line_code_to_src_row()

        src_rows = set(line_code_to_src.values())
        actual = {r: 0.0 for r in src_rows}

        maps = self.env["mbr.account.map"].search(
            [("company_id", "=", self.company_id.id)]
        )
        if not maps:
            return actual

        acc_to_line = {m.account_id.id: m.line_code for m in maps}

        aml = self.env["account.move.line"]
        domain = [
            ("company_id", "=", self.company_id.id),
            ("date", ">=", date_from),
            ("date", "<=", date_to),
        ]
        if self.target_move == "posted":
            domain.append(("parent_state", "=", "posted"))
        if self.journal_ids:
            domain.append(("journal_id", "in", self.journal_ids.ids))

        fields = ["balance", "account_id"]
        groupby = ["account_id"]

        result = aml.read_group(domain, fields, groupby, lazy=False)

        for row in result:
            account = row.get("account_id")
            if not account:
                continue
            acc_id = account[0]
            line_code = acc_to_line.get(acc_id)
            if not line_code:
                continue
            src_row = line_code_to_src.get(line_code)
            if not src_row:
                continue

            amount = abs(row.get("balance", 0.0) or 0.0)
            actual[src_row] += amount

        return actual

    # ---------------- BUDGET DATA -----------------

    def _get_budget_matrix(self, date_from, date_to):
        """Aggregate budget amounts from account.report.budget.item."""
        self.ensure_one()
        line_code_to_src = self._line_code_to_src_row()
        src_rows = set(line_code_to_src.values())

        budget = {r: 0.0 for r in src_rows}
        budget_ytd = {r: 0.0 for r in src_rows}

        maps = self.env["mbr.account.map"].search(
            [("company_id", "=", self.company_id.id)]
        )
        if not maps:
            return budget, budget_ytd

        acc_to_line = {m.account_id.id: m.line_code for m in maps}

        BudgetItem = self.env["account.report.budget.item"]
        dt_from = fields.Date.to_date(date_from)
        dt_to = fields.Date.to_date(date_to)
        if not dt_from or not dt_to:
            return budget, budget_ytd

        ytd_start = dt_to.replace(month=1, day=1)
        mapped_account_ids = list(acc_to_line)
        base_domain = [("budget_id.company_id", "=", self.company_id.id)]
        if mapped_account_ids:
            base_domain.append(("account_id", "in", mapped_account_ids))

        def _accumulate(domain, target):
            rows = BudgetItem.read_group(domain, ["amount", "account_id"], ["account_id"], lazy=False)
            for row in rows:
                account = row.get("account_id")
                if not account:
                    continue
                acc_id = account[0]
                line_code = acc_to_line.get(acc_id)
                if not line_code:
                    continue
                src_row = line_code_to_src.get(line_code)
                if not src_row:
                    continue
                target[src_row] += abs(row.get("amount", 0.0) or 0.0)

        period_domain = base_domain + [
            ("date", ">=", dt_from),
            ("date", "<=", dt_to),
        ]
        _accumulate(period_domain, budget)

        ytd_domain = base_domain + [
            ("date", ">=", ytd_start),
            ("date", "<=", dt_to),
        ]
        _accumulate(ytd_domain, budget_ytd)

        return budget, budget_ytd

    # ---------------- MAIN COMPUTATION -----------------

    def _compute_period(self, date_from, date_to):
        self.ensure_one()
        scale = self.scale or 1.0

        current_label, ytd_label, period_label = self._period_labels(date_from, date_to)

        # main period actual
        actual_period = self._get_actual_matrix(date_from, date_to)

        # ytd from Jan 1 to date_to
        dt = fields.Date.to_date(date_to)
        ytd_from = dt.replace(month=1, day=1)
        actual_ytd_raw = self._get_actual_matrix(ytd_from, date_to)

        budget, budget_ytd = self._get_budget_matrix(date_from, date_to)

        lines = []
        rev_codes = []
        cogs_codes = []
        opex_codes = []
        fin_codes = []

        for ld in self.LINE_DEFS:
            if ld["section"] == "revenue":
                rev_codes.append(ld["code"])
            elif ld["section"] == "cogs":
                cogs_codes.append(ld["code"])
            elif ld["section"] == "opex":
                opex_codes.append(ld["code"])
            elif ld["section"] == "finance":
                fin_codes.append(ld["code"])

        tmp_by_code = {}

        for ld in self.LINE_DEFS:
            code = ld["code"]
            name = ld["name"]
            src_row = ld["src_row"]

            period_actual_val = actual_period.get(src_row, 0.0)
            curr_actual = period_actual_val / scale
            curr_budget = budget.get(src_row, 0.0) / scale
            curr_diff = curr_actual - curr_budget
            curr_diff_pct = self._safe_div(curr_diff, curr_budget)

            ytd_actual = actual_ytd_raw.get(src_row, 0.0) / scale
            ytd_budget = budget_ytd.get(src_row, 0.0) / scale
            ytd_diff = ytd_actual - ytd_budget
            ytd_diff_pct = self._safe_div(ytd_diff, ytd_budget)

            line_vals = {
                "code": code,
                "name": name,
                "section": ld["section"],
                "curr_actual": curr_actual,
                "curr_budget": curr_budget,
                "curr_diff": curr_diff,
                "curr_diff_pct": curr_diff_pct,
                "ytd_actual": ytd_actual,
                "ytd_budget": ytd_budget,
                "ytd_diff": ytd_diff,
                "ytd_diff_pct": ytd_diff_pct,
                "curr_pct_revenue": 0.0,
                "ytd_pct_revenue": 0.0,
                "curr_budget_pct_revenue": 0.0,
                "ytd_budget_pct_revenue": 0.0,
            }
            tmp_by_code[code] = line_vals
            lines.append(line_vals)

        def sum_codes(codes, key):
            return sum(tmp_by_code[c]["curr_" + key] for c in codes), sum(
                tmp_by_code[c]["ytd_" + key] for c in codes
            )

        total_rev_curr, total_rev_ytd = sum_codes(rev_codes, "actual")
        total_rev_budget_curr, total_rev_budget_ytd = sum_codes(rev_codes, "budget")
        total_rev_diff_curr, total_rev_diff_ytd = sum_codes(rev_codes, "diff")

        total_cogs_curr, total_cogs_ytd = sum_codes(cogs_codes, "actual")
        total_cogs_budget_curr, total_cogs_budget_ytd = sum_codes(cogs_codes, "budget")
        total_cogs_diff_curr, total_cogs_diff_ytd = sum_codes(cogs_codes, "diff")

        gross_curr = total_rev_curr - total_cogs_curr
        gross_ytd = total_rev_ytd - total_cogs_ytd
        gross_budget_curr = total_rev_budget_curr - total_cogs_budget_curr
        gross_budget_ytd = total_rev_budget_ytd - total_cogs_budget_ytd
        gross_diff_curr = gross_curr - gross_budget_curr
        gross_diff_ytd = gross_ytd - gross_budget_ytd

        total_opex_curr, total_opex_ytd = sum_codes(opex_codes, "actual")
        total_opex_budget_curr, total_opex_budget_ytd = sum_codes(opex_codes, "budget")
        total_opex_diff_curr, total_opex_diff_ytd = sum_codes(opex_codes, "diff")

        net_before_fin_curr = gross_curr - total_opex_curr
        net_before_fin_ytd = gross_ytd - total_opex_ytd
        net_before_fin_budget_curr = gross_budget_curr - total_opex_budget_curr
        net_before_fin_budget_ytd = gross_budget_ytd - total_opex_budget_ytd
        net_before_fin_diff_curr = net_before_fin_curr - net_before_fin_budget_curr
        net_before_fin_diff_ytd = net_before_fin_ytd - net_before_fin_budget_ytd

        total_fin_curr, total_fin_ytd = sum_codes(fin_codes, "actual")
        total_fin_budget_curr, total_fin_budget_ytd = sum_codes(fin_codes, "budget")
        total_fin_diff_curr, total_fin_diff_ytd = sum_codes(fin_codes, "diff")

        net_before_tax_curr = net_before_fin_curr - total_fin_curr
        net_before_tax_ytd = net_before_fin_ytd - total_fin_ytd
        net_before_tax_budget_curr = net_before_fin_budget_curr - total_fin_budget_curr
        net_before_tax_budget_ytd = net_before_fin_budget_ytd - total_fin_budget_ytd
        net_before_tax_diff_curr = net_before_tax_curr - net_before_tax_budget_curr
        net_before_tax_diff_ytd = net_before_tax_ytd - net_before_tax_budget_ytd

        cit_curr = max(net_before_tax_curr * 0.20, 0.0)
        cit_ytd = max(net_before_tax_ytd * 0.20, 0.0)
        cit_budget_curr = max(net_before_tax_budget_curr * 0.20, 0.0)
        cit_budget_ytd = max(net_before_tax_budget_ytd * 0.20, 0.0)
        cit_diff_curr = cit_curr - cit_budget_curr
        cit_diff_ytd = cit_ytd - cit_budget_ytd

        net_after_tax_curr = net_before_tax_curr - cit_curr
        net_after_tax_ytd = net_before_tax_ytd - cit_ytd
        net_after_tax_budget_curr = net_before_tax_budget_curr - cit_budget_curr
        net_after_tax_budget_ytd = net_before_tax_budget_ytd - cit_budget_ytd
        net_after_tax_diff_curr = net_after_tax_curr - net_after_tax_budget_curr
        net_after_tax_diff_ytd = net_after_tax_ytd - net_after_tax_budget_ytd

        for line in lines:
            line["curr_pct_revenue"] = self._safe_div(
                line["curr_actual"], total_rev_curr
            )
            line["ytd_pct_revenue"] = self._safe_div(
                line["ytd_actual"], total_rev_ytd
            )
            line["curr_budget_pct_revenue"] = self._safe_div(
                line["curr_budget"], total_rev_curr
            )
            line["ytd_budget_pct_revenue"] = self._safe_div(
                line["ytd_budget"], total_rev_ytd
            )
            line["curr_diff_pct"] = self._safe_div(line["curr_diff"], line["curr_budget"])
            line["ytd_diff_pct"] = self._safe_div(line["ytd_diff"], line["ytd_budget"])

        totals = {
            "total_rev_curr": total_rev_curr,
            "total_rev_ytd": total_rev_ytd,
            "total_rev_budget_curr": total_rev_budget_curr,
            "total_rev_budget_ytd": total_rev_budget_ytd,
            "total_rev_diff_curr": total_rev_diff_curr,
            "total_rev_diff_ytd": total_rev_diff_ytd,
            "total_cogs_curr": total_cogs_curr,
            "total_cogs_ytd": total_cogs_ytd,
            "total_cogs_budget_curr": total_cogs_budget_curr,
            "total_cogs_budget_ytd": total_cogs_budget_ytd,
            "total_cogs_diff_curr": total_cogs_diff_curr,
            "total_cogs_diff_ytd": total_cogs_diff_ytd,
            "gross_curr": gross_curr,
            "gross_ytd": gross_ytd,
            "gross_budget_curr": gross_budget_curr,
            "gross_budget_ytd": gross_budget_ytd,
            "gross_diff_curr": gross_diff_curr,
            "gross_diff_ytd": gross_diff_ytd,
            "total_opex_curr": total_opex_curr,
            "total_opex_ytd": total_opex_ytd,
            "total_opex_budget_curr": total_opex_budget_curr,
            "total_opex_budget_ytd": total_opex_budget_ytd,
            "total_opex_diff_curr": total_opex_diff_curr,
            "total_opex_diff_ytd": total_opex_diff_ytd,
            "net_before_fin_curr": net_before_fin_curr,
            "net_before_fin_ytd": net_before_fin_ytd,
            "net_before_fin_budget_curr": net_before_fin_budget_curr,
            "net_before_fin_budget_ytd": net_before_fin_budget_ytd,
            "net_before_fin_diff_curr": net_before_fin_diff_curr,
            "net_before_fin_diff_ytd": net_before_fin_diff_ytd,
            "total_fin_curr": total_fin_curr,
            "total_fin_ytd": total_fin_ytd,
            "total_fin_budget_curr": total_fin_budget_curr,
            "total_fin_budget_ytd": total_fin_budget_ytd,
            "total_fin_diff_curr": total_fin_diff_curr,
            "total_fin_diff_ytd": total_fin_diff_ytd,
            "net_before_tax_curr": net_before_tax_curr,
            "net_before_tax_ytd": net_before_tax_ytd,
            "net_before_tax_budget_curr": net_before_tax_budget_curr,
            "net_before_tax_budget_ytd": net_before_tax_budget_ytd,
            "net_before_tax_diff_curr": net_before_tax_diff_curr,
            "net_before_tax_diff_ytd": net_before_tax_diff_ytd,
            "cit_curr": cit_curr,
            "cit_ytd": cit_ytd,
            "cit_budget_curr": cit_budget_curr,
            "cit_budget_ytd": cit_budget_ytd,
            "cit_diff_curr": cit_diff_curr,
            "cit_diff_ytd": cit_diff_ytd,
            "net_after_tax_curr": net_after_tax_curr,
            "net_after_tax_ytd": net_after_tax_ytd,
            "net_after_tax_budget_curr": net_after_tax_budget_curr,
            "net_after_tax_budget_ytd": net_after_tax_budget_ytd,
            "net_after_tax_diff_curr": net_after_tax_diff_curr,
            "net_after_tax_diff_ytd": net_after_tax_diff_ytd,
        }

        # Subtotals for 1.1 and 2.1
        total_rev_1_1_curr, total_rev_1_1_ytd = sum_codes(["1.1.1", "1.1.2"], "actual")
        total_rev_1_1_budget_curr, total_rev_1_1_budget_ytd = sum_codes(["1.1.1", "1.1.2"], "budget")
        total_rev_1_1_diff_curr, total_rev_1_1_diff_ytd = sum_codes(["1.1.1", "1.1.2"], "diff")

        totals.update({
            "total_rev_1_1_curr": total_rev_1_1_curr,
            "total_rev_1_1_ytd": total_rev_1_1_ytd,
            "total_rev_1_1_budget_curr": total_rev_1_1_budget_curr,
            "total_rev_1_1_budget_ytd": total_rev_1_1_budget_ytd,
            "total_rev_1_1_diff_curr": total_rev_1_1_diff_curr,
            "total_rev_1_1_diff_ytd": total_rev_1_1_diff_ytd,
        })

        total_cogs_2_1_curr, total_cogs_2_1_ytd = sum_codes(["2.1.1", "2.1.2"], "actual")
        total_cogs_2_1_budget_curr, total_cogs_2_1_budget_ytd = sum_codes(["2.1.1", "2.1.2"], "budget")
        total_cogs_2_1_diff_curr, total_cogs_2_1_diff_ytd = sum_codes(["2.1.1", "2.1.2"], "diff")

        totals.update({
            "total_cogs_2_1_curr": total_cogs_2_1_curr,
            "total_cogs_2_1_ytd": total_cogs_2_1_ytd,
            "total_cogs_2_1_budget_curr": total_cogs_2_1_budget_curr,
            "total_cogs_2_1_budget_ytd": total_cogs_2_1_budget_ytd,
            "total_cogs_2_1_diff_curr": total_cogs_2_1_diff_curr,
            "total_cogs_2_1_diff_ytd": total_cogs_2_1_diff_ytd,
        })

        return {
            "current_label": current_label,
            "ytd_label": ytd_label,
            "period_label": period_label,
            "scale": scale,
            "lines": lines,
            "totals": totals,
            "date_from": date_from,
            "date_to": date_to,
        }

    @api.model
    def _year_selection(self):
        current = date.today().year
        return [(str(y), str(y)) for y in range(current - 100, current + 101)]

    def compute_mbr(self):
        self.ensure_one()
        year_int = int(self.year) if self.year else date.today().year
        
        if self.period_type == "quarter":
            q = int(self.quarter) if self.quarter else 1
            start_month = (q - 1) * 3 + 1
            end_month = start_month + 2
            last_day = calendar.monthrange(year_int, end_month)[1]
            date_from = date(year_int, start_month, 1)
            date_to = date(year_int, end_month, last_day)
        else:
            month_int = int(self.month) if self.month else date.today().month
            last_day = calendar.monthrange(year_int, month_int)[1]
            date_from = date(year_int, month_int, 1)
            date_to = date(year_int, month_int, last_day)

        main_data = self._compute_period(date_from, date_to)
        compare_data = False
        if self.compare and self.compare_date_from and self.compare_date_to:
            compare_data = self._compute_period(self.compare_date_from, self.compare_date_to)

        response = {
            "main": main_data,
            "comparison": compare_data,
            "scale": self.scale or 1.0,
        }
        response.update(main_data)
        return response
