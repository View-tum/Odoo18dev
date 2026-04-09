from odoo import models, fields, api, _
from collections import defaultdict
from odoo.exceptions import UserError


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    def _check_budget_availability(self):
        """
        TH: (Internal) ตรวจสอบว่าคำขอซื้อนี้ใช้งบประมาณเกินกว่าที่กำหนดไว้ในโครงการหรือไม่
        EN: (Internal) Checks whether this purchase request exceeds the allocated budget for the project.
        """
        needed_accounts = set()
        dates = set()
        line_analytics = []

        for request in self:
            request_date = request.date_start or fields.Date.today()
            dates.add(request_date)

            for line in request.line_ids:
                if line.cancelled or not getattr(line, "analytic_distribution", False):
                    continue

                for account_id_str, percentage in line.analytic_distribution.items():
                    analytic_account_ids = [int(x) for x in account_id_str.split(",")]
                    for account_id in analytic_account_ids:
                        needed_accounts.add(account_id)
                        line_analytics.append((line, account_id, percentage))

        if not needed_accounts:
            return False

        Project = self.env["project.project"]
        BudgetLine = self.env["budget.line"]
        AnalyticAccount = self.env["account.analytic.account"]

        projects = Project.search([("account_id", "in", list(needed_accounts))])
        project_map = {p.account_id.id: p for p in projects}

        accounts = AnalyticAccount.browse(list(needed_accounts))
        budget_lines_cache = defaultdict(list)

        accounts_by_plan = defaultdict(lambda: self.env["account.analytic.account"])
        for account in accounts:
            if account.plan_id:
                accounts_by_plan[account.plan_id] += account

        min_date = min(dates)
        max_date = max(dates)

        for plan, plan_accounts in accounts_by_plan.items():
            plan_column = plan._column_name()
            domain = [
                (plan_column, "in", plan_accounts.ids),
                ("date_from", "<=", max_date),
                ("date_to", ">=", min_date),
            ]
            fetched_lines = BudgetLine.search(domain)
            for bl in fetched_lines:
                acc_ref = bl[plan_column]
                acc_id = acc_ref.id if acc_ref else False
                if acc_id:
                    budget_lines_cache[acc_id].append(bl)

        usage_map = defaultdict(float)
        bl_to_project_map = {}

        for line, account_id, percentage in line_analytics:
            project = project_map.get(account_id)
            if not project:
                continue

            line_date = line.request_id.date_start or fields.Date.today()
            relevant_bls = budget_lines_cache.get(account_id, [])

            target_bl = None
            for bl in relevant_bls:
                if bl.date_from <= line_date <= bl.date_to:
                    target_bl = bl
                    break

            if not target_bl:
                continue

            amount_currency = line.estimated_cost
            if (
                line.currency_id
                and target_bl.currency_id
                and line.currency_id != target_bl.currency_id
            ):
                amount_converted = line.currency_id._convert(
                    amount_currency, target_bl.currency_id, line.company_id, line_date
                )
            else:
                amount_converted = amount_currency

            request_amount = amount_converted * (percentage / 100.0)
            usage_map[target_bl] += request_amount
            bl_to_project_map[target_bl] = project

        for budget_line, total_request in usage_map.items():
            current_usage = budget_line.committed_amount + total_request
            if current_usage > budget_line.budget_amount:
                over_amount = current_usage - budget_line.budget_amount
                project = bl_to_project_map.get(budget_line)

                message = (
                    f"  • ไม่สามารถดำเนินการได้ เนื่องจากงบประมาณโครงการเต็ม!\n"
                    f"  • โครงการ: {project.name if project else '-'}\n"
                    f"  • งบประมาณ: {budget_line.name}\n"
                    f"  • งบตั้งต้น: {budget_line.budget_amount:,.2f}\n"
                    f"  • ใช้ไปแล้ว: {budget_line.committed_amount:,.2f}\n"
                    f"  • ขอยื่นเพิ่มรอบนี้: {total_request:,.2f}\n"
                    f"  • เกินงบไป: {over_amount:,.2f}"
                )

                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Budget Exceeded / งบประมาณไม่เพียงพอ",
                        "message": message,
                        "type": "danger",
                        "sticky": True,
                    },
                }

        return False

    def approval_action_button(self, *args, **kwargs):
        """
        TH: (Override) ดักจับปุ่มอนุมัติเพื่อตรวจสอบงบประมาณก่อน หากผ่านเกณฑ์จึงจะเรียกฟังก์ชันอนุมัติเดิมของระบบ
        EN: (Override) Intercepts the approval button to check the budget first. If valid, proceeds with the original approval function.
        """
        budget_error = self._check_budget_availability()

        if budget_error:
            return budget_error

        return super(PurchaseRequest, self).approval_action_button(*args, **kwargs)
