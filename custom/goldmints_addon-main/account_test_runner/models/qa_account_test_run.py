import math
import re
import time
import traceback

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.modules.module import get_module_path


class QaAccountTestRun(models.Model):
    _name = "qa.account.test.run"
    _description = "Accounting Test Run"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(default=lambda self: self.env["ir.sequence"].next_by_code("qa.account.test.run") or _("New"), readonly=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("running", "Running"),
            ("done", "Done"),
            ("failed", "Failed"),
        ],
        default="draft",
        tracking=True,
        readonly=True,
    )
    started_at = fields.Datetime(readonly=True)
    finished_at = fields.Datetime(readonly=True)
    user_id = fields.Many2one("res.users", default=lambda self: self.env.user, readonly=True)
    db_name = fields.Char(default=lambda self: self.env.cr.dbname, readonly=True)
    line_ids = fields.One2many("qa.account.test.run.line", "run_id", readonly=True)

    total_count = fields.Integer(compute="_compute_counts", store=True)
    pass_count = fields.Integer(compute="_compute_counts", store=True)
    fail_count = fields.Integer(compute="_compute_counts", store=True)
    skip_count = fields.Integer(compute="_compute_counts", store=True)

    @api.depends("line_ids.status")
    def _compute_counts(self):
        for run in self:
            run.total_count = len(run.line_ids)
            run.pass_count = len(run.line_ids.filtered(lambda l: l.status == "pass"))
            run.fail_count = len(run.line_ids.filtered(lambda l: l.status == "fail"))
            run.skip_count = len(run.line_ids.filtered(lambda l: l.status == "skip"))

    def action_run_full_suite(self):
        for run in self:
            run._run_full_suite()
        return True

    def _run_full_suite(self):
        self.ensure_one()
        self.write(
            {
                "state": "running",
                "started_at": fields.Datetime.now(),
                "finished_at": False,
                "line_ids": [(5, 0, 0)],
            }
        )

        cases = [
            ("TC01", "Modules Installed", self._case_tc01_modules_installed),
            ("TC02", "Unpaid Documents Exist", self._case_tc02_data_unpaid_exists),
            ("TC00", "Manual Journal Precheck", self._case_tc00_precheck_manual_journal),
            ("TC03", "Group Payment Single Wizard", self._case_tc03_gp_single_wizard),
            ("TC09", "Group Payment Open Pay Wizard", self._case_tc09_gp_action_open_wizard),
            ("TC03_1", "Wizard Amount Positive", self._case_tc031_wizard_amount_positive),
            ("TC04", "Group Payment Two Same Currency", self._case_tc04_gp_two_same_currency),
            ("TC05", "Group Payment Mixed Currency Blocked", self._case_tc05_gp_mixed_currency_block),
            ("TC06", "Currency Switch Recompute", self._case_tc06_currency_switch_recompute),
            ("TC07", "Manual FX Same Currency Guard", self._case_tc07_manual_fx_same_currency_guard),
            ("TC08", "Source Guard Account Invoice", self._case_tc08_source_guard_account_invoice),
            ("TC12", "Allocation Map Applied on Create", self._case_tc12_allocation_map_on_create),
            ("TC10", "Group Payment Create Payment", self._case_tc10_gp_create_payment),
            ("TC11", "Group Payment Payer Partner Propagation", self._case_tc11_gp_payer_partner_propagation),
        ]

        for sequence, (code, name, method) in enumerate(cases, start=1):
            status, message, duration = self._run_case_with_savepoint(code, method)
            self.env["qa.account.test.run.line"].create(
                {
                    "run_id": self.id,
                    "sequence": sequence,
                    "case_code": code,
                    "case_name": name,
                    "status": status,
                    "message": message,
                    "duration_ms": duration,
                }
            )

        self.invalidate_recordset(["line_ids", "fail_count"])
        final_state = "done" if not self.line_ids.filtered(lambda line: line.status == "fail") else "failed"
        self.write({"state": final_state, "finished_at": fields.Datetime.now()})

    def _run_case_with_savepoint(self, code, method):
        self.ensure_one()
        t0 = time.perf_counter()
        savepoint = "qa_case_%s_%s" % (self.id, re.sub(r"[^a-zA-Z0-9_]", "_", code.lower()))

        self.env.cr.execute('SAVEPOINT "%s"' % savepoint)
        try:
            status, message = method()
            if status not in ("pass", "fail", "skip"):
                status = "fail"
                message = _("Invalid test status returned by case.")
        except Exception as exc:  # pragma: no cover - defensive
            status = "fail"
            message = "%s\n%s" % (exc, traceback.format_exc(limit=1))
        finally:
            self.env.cr.execute('ROLLBACK TO SAVEPOINT "%s"' % savepoint)
            self.env.cr.execute('RELEASE SAVEPOINT "%s"' % savepoint)
            self.env.clear()

        duration = int((time.perf_counter() - t0) * 1000)
        return status, str(message or ""), duration

    # ---------------------------
    # Helpers
    # ---------------------------

    def _required_modules(self):
        return {"account_customer_group_payment", "bi_manual_currency_exchange_rate"}

    def _get_model(self, model_name):
        model_cls = self.env.registry.get(model_name)
        if model_cls is not None:
            return self.env[model_name]
        return False

    def _installed_modules(self):
        return set(
            self.env["ir.module.module"].search(
                [("name", "in", list(self._required_modules() | {"account_payment_multi_allocation"})), ("state", "=", "installed")]
            ).mapped("name")
        )

    def _get_unpaid_moves(self, limit=500):
        return self.env["account.move"].search(
            [
                ("move_type", "in", ["out_invoice", "out_refund"]),
                ("state", "=", "posted"),
                ("payment_state", "!=", "paid"),
            ],
            limit=limit,
        )

    def _get_journals(self):
        return self.env["account.journal"].search(
            [
                ("type", "in", ("bank", "cash")),
                ("company_id", "=", self.env.company.id),
            ]
        )

    def _has_manual_inbound_method(self, journal):
        return any(line.payment_method_id.code == "manual" for line in journal.inbound_payment_method_line_ids)

    def _is_safe_for_currency(self, journal, currency):
        if journal.currency_id and journal.currency_id != currency:
            return False
        account = journal.default_account_id
        if account and account.currency_id and account.currency_id != currency:
            return False
        return True

    def _find_safe_manual_journal(self, currency):
        journals = self._get_journals().filtered(self._has_manual_inbound_method)
        for journal in journals:
            if self._is_safe_for_currency(journal, currency):
                return journal
        return journals[:1]

    def _find_single_unpaid_move(self):
        unpaid = self._get_unpaid_moves()
        return unpaid[:1]

    def _find_same_currency_pair(self):
        unpaid = self._get_unpaid_moves()
        by_currency = {}
        for move in unpaid:
            by_currency.setdefault(move.currency_id.id, []).append(move)
        for moves in by_currency.values():
            if len(moves) >= 2:
                return moves[0], moves[1]
        return self.env["account.move"], self.env["account.move"]

    def _find_mixed_currency_pair(self):
        unpaid = self._get_unpaid_moves()
        by_currency = {}
        for move in unpaid:
            by_currency.setdefault(move.currency_id.id, []).append(move)
        currency_ids = list(by_currency.keys())
        if len(currency_ids) < 2:
            return self.env["account.move"], self.env["account.move"]
        return by_currency[currency_ids[0]][0], by_currency[currency_ids[1]][0]

    def _build_group_payment_with_lines(self, moves, journal):
        gp_model = self._get_model("account.customer.group.payment")
        line_model = self._get_model("account.customer.group.payment.line")
        if gp_model is False or line_model is False:
            return False, _("Model account.customer.group.payment not found."), False, False

        moves = moves.exists()
        if not moves:
            return False, _("No move to build group payment."), False, False

        first_move = moves[0]
        gp = gp_model.create(
            {
                "company_id": self.env.company.id,
                "company_group_id": first_move.partner_id.commercial_partner_id.id,
                "payer_partner_id": first_move.partner_id.commercial_partner_id.id,
                "payment_date": fields.Date.context_today(self),
                "payment_journal_id": journal.id if journal else False,
            }
        )

        for move in moves:
            line_model.create(
                {
                    "payment_id": gp.id,
                    "move_id": move.id,
                    "partner_id": move.partner_id.id,
                    "currency_id": move.currency_id.id,
                    "amount_total": abs(move.amount_total),
                    "amount_residual": abs(move.amount_residual),
                    "amount_to_pay": abs(move.amount_residual),
                    "is_selected": True,
                }
            )

        try:
            action = gp.action_confirm_payment()
        except Exception as exc:
            return False, str(exc), gp, False

        wizard = self.env["account.payment.register"].browse(action.get("res_id")) if action else False
        return True, _("OK"), gp, (action, wizard)

    # ---------------------------
    # Test cases
    # ---------------------------

    def _case_tc01_modules_installed(self):
        installed = self._installed_modules()
        ok = self._required_modules().issubset(installed)
        return ("pass" if ok else "fail", "installed=%s" % sorted(list(installed)))

    def _case_tc02_data_unpaid_exists(self):
        count = len(self._get_unpaid_moves())
        return ("pass" if count > 0 else "fail", "count=%s" % count)

    def _case_tc00_precheck_manual_journal(self):
        move = self._find_single_unpaid_move()
        if not move:
            return "skip", _("No unpaid move.")
        journal = self._find_safe_manual_journal(move.currency_id)
        return ("pass" if journal else "fail", "journal_id=%s" % (journal.id if journal else False))

    def _case_tc03_gp_single_wizard(self):
        move = self._find_single_unpaid_move()
        if not move:
            return "skip", _("No unpaid move.")
        journal = self._find_safe_manual_journal(move.currency_id)
        ok, message, _, wiz_bundle = self._build_group_payment_with_lines(move, journal)
        if not ok:
            return "fail", message
        action, _wizard = wiz_bundle
        return "pass", "res_id=%s" % action.get("res_id")

    def _case_tc09_gp_action_open_wizard(self):
        move = self._find_single_unpaid_move()
        if not move:
            return "skip", _("No unpaid move.")
        journal = self._find_safe_manual_journal(move.currency_id)
        ok, message, _, wiz_bundle = self._build_group_payment_with_lines(move, journal)
        if not ok:
            return "fail", message
        action, _wizard = wiz_bundle
        return ("pass" if action.get("target") == "new" else "fail", "target=%s" % action.get("target"))

    def _case_tc031_wizard_amount_positive(self):
        move = self._find_single_unpaid_move()
        if not move:
            return "skip", _("No unpaid move.")
        journal = self._find_safe_manual_journal(move.currency_id)
        ok, message, _, wiz_bundle = self._build_group_payment_with_lines(move, journal)
        if not ok:
            return "fail", message
        _action, wizard = wiz_bundle
        return ("pass" if wizard and wizard.amount > 0 else "fail", "amount=%s" % (wizard.amount if wizard else 0.0))

    def _case_tc04_gp_two_same_currency(self):
        move_a, move_b = self._find_same_currency_pair()
        if not move_a or not move_b:
            return "skip", _("Not enough same-currency unpaid moves.")
        journal = self._find_safe_manual_journal(move_a.currency_id)
        ok, message, _, wiz_bundle = self._build_group_payment_with_lines(move_a | move_b, journal)
        if not ok:
            return "fail", message
        action, wizard = wiz_bundle
        return ("pass" if wizard else "fail", "res_id=%s amount=%s" % (action.get("res_id"), wizard.amount if wizard else 0.0))

    def _case_tc05_gp_mixed_currency_block(self):
        move_a, move_b = self._find_mixed_currency_pair()
        if not move_a or not move_b:
            return "skip", _("Need mixed currency unpaid moves.")

        journal = self._find_safe_manual_journal(move_a.currency_id)
        gp_model = self._get_model("account.customer.group.payment")
        line_model = self._get_model("account.customer.group.payment.line")
        if gp_model is False or line_model is False:
            return "skip", _("Group payment model not found.")

        gp = gp_model.create(
            {
                "company_id": self.env.company.id,
                "company_group_id": move_a.partner_id.commercial_partner_id.id,
                "payer_partner_id": move_a.partner_id.commercial_partner_id.id,
                "payment_date": fields.Date.context_today(self),
                "payment_journal_id": journal.id if journal else False,
            }
        )

        for move in (move_a, move_b):
            line_model.create(
                {
                    "payment_id": gp.id,
                    "move_id": move.id,
                    "partner_id": move.partner_id.id,
                    "currency_id": move.currency_id.id,
                    "amount_total": abs(move.amount_total),
                    "amount_residual": abs(move.amount_residual),
                    "amount_to_pay": abs(move.amount_residual),
                    "is_selected": True,
                }
            )

        try:
            gp.action_confirm_payment()
            return "fail", _("Expected mixed-currency block was not raised.")
        except UserError as exc:
            return "pass", str(exc)

    def _case_tc06_currency_switch_recompute(self):
        move = self._get_unpaid_moves().filtered(lambda m: m.currency_id != self.env.company.currency_id)[:1]
        if not move:
            return "skip", _("No foreign-currency unpaid move.")

        wizard = self.env["account.payment.register"].with_context(
            active_model="account.move",
            active_ids=[move.id],
        ).create({})
        before = wizard.amount
        wizard.currency_id = self.env.company.currency_id
        if hasattr(wizard, "_onchange_journal"):
            wizard._onchange_journal()
        if hasattr(wizard, "_onchange_currency"):
            wizard._onchange_currency()
        wizard._compute_amount()
        after = wizard.amount

        changed = not math.isclose(before or 0.0, after or 0.0, rel_tol=1e-9, abs_tol=1e-6)
        ok = changed and after > 0
        return ("pass" if ok else "fail", "%s:%s -> %s:%s" % (move.currency_id.name, before, self.env.company.currency_id.name, after))

    def _case_tc07_manual_fx_same_currency_guard(self):
        move = self._get_unpaid_moves().filtered(lambda m: m.currency_id == self.env.company.currency_id)[:1]
        if not move:
            return "skip", _("No company-currency unpaid move.")

        wizard = self.env["account.payment.register"].with_context(
            active_model="account.move",
            active_ids=[move.id],
        ).create({})

        if not hasattr(wizard, "check_currency_id"):
            return "skip", _("Manual FX guard method not found.")

        wizard.manual_currency_rate_active = True
        wizard.manual_currency_rate = 35.0
        wizard.check_currency_id()

        ok = (not wizard.manual_currency_rate_active) and float(wizard.manual_currency_rate or 0.0) == 0.0
        return ("pass" if ok else "fail", "active=%s rate=%s" % (wizard.manual_currency_rate_active, wizard.manual_currency_rate))

    def _case_tc08_source_guard_account_invoice(self):
        module_path = get_module_path("bi_manual_currency_exchange_rate")
        if not module_path:
            return "skip", _("Module path not found.")

        file_path = "%s/models/account_invoice.py" % module_path
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as file_handle:
                source = file_handle.read()
        except OSError as exc:
            return "fail", str(exc)

        ok_super_residual = (
            "_prepare_move_line_residual_amounts" in source
            and "return super()._prepare_move_line_residual_amounts" in source
        )
        ok_super_partial = (
            "_prepare_reconciliation_single_partial" in source
            and "return super()._prepare_reconciliation_single_partial" in source
        )
        ok_split_unit = "price_unit_base = price_subtotal / po_line.product_qty" in source

        ok = ok_super_residual and ok_super_partial and ok_split_unit
        return (
            "pass" if ok else "fail",
            "super_residual=%s super_partial=%s split_unit=%s" % (ok_super_residual, ok_super_partial, ok_split_unit),
        )

    def _case_tc12_allocation_map_on_create(self):
        move_a, move_b = self._find_same_currency_pair()
        move = move_b or move_a
        if not move:
            return "skip", _("Not enough same-currency unpaid moves.")

        if "allocation_line_ids" not in self.env["account.payment.register"]._fields:
            return "skip", _("allocation_line_ids is not available.")

        target_amount = abs(move.amount_residual) / 2.0 if abs(move.amount_residual) else 0.0
        wizard = self.env["account.payment.register"].with_context(
            active_model="account.move",
            active_ids=[move.id],
            is_group_payment=True,
            group_payment_amounts_by_move_id={move.id: target_amount},
        ).create({})

        allocation_lines = wizard.allocation_line_ids.filtered(lambda line: line.move_line_id.move_id.id == move.id)
        if not allocation_lines:
            return "fail", _("No allocation lines were generated.")

        actual = sum(abs(line.amount_to_pay or 0.0) for line in allocation_lines)
        expected = min(abs(move.amount_residual), abs(target_amount))
        ok = math.isclose(actual, expected, rel_tol=1e-9, abs_tol=0.01)
        return ("pass" if ok else "fail", "expected=%s actual=%s lines=%s" % (expected, actual, len(allocation_lines)))

    def _case_tc10_gp_create_payment(self):
        move = self._find_single_unpaid_move()
        if not move:
            return "skip", _("No unpaid move.")

        journal = self._find_safe_manual_journal(move.currency_id)
        ok, message, group_payment, wiz_bundle = self._build_group_payment_with_lines(move, journal)
        if not ok:
            return "fail", message

        action, wizard = wiz_bundle
        if not wizard:
            return "fail", _("Wizard was not created.")

        safe_journal = self._find_safe_manual_journal(wizard.currency_id)
        if safe_journal and wizard.journal_id != safe_journal:
            wizard.journal_id = safe_journal.id
            if hasattr(wizard, "_onchange_journal"):
                wizard._onchange_journal()

        manual_line = wizard.journal_id.inbound_payment_method_line_ids.filtered(lambda line: line.payment_method_id.code == "manual")[:1]
        if not manual_line:
            return "skip", _("Manual payment method is missing on selected journal.")

        wizard.payment_method_line_id = manual_line.id
        context = (action or {}).get("context") if isinstance(action, dict) else {}
        wizard.with_context(**(context or {})).action_create_payments()

        group_payment.invalidate_recordset(["generated_payment_ids", "state"])
        payment = self.env["account.payment"].search(
            [("id", "in", group_payment.generated_payment_ids.ids)],
            order="id desc",
            limit=1,
        )
        if not payment:
            payment = self.env["account.payment"].search(
                [
                    ("ref", "=", move.name),
                    ("partner_id", "=", group_payment.payer_partner_id.id),
                ],
                order="id desc",
                limit=1,
            )

        ok = bool(payment)
        return ("pass" if ok else "fail", "group_state=%s payment_id=%s" % (group_payment.state, payment.id if payment else False))

    def _case_tc11_gp_payer_partner_propagation(self):
        move = self._find_single_unpaid_move()
        if not move:
            return "skip", _("No unpaid move.")

        journal = self._find_safe_manual_journal(move.currency_id)
        ok, message, group_payment, wiz_bundle = self._build_group_payment_with_lines(move, journal)
        if not ok:
            return "fail", message

        action, wizard = wiz_bundle
        if not wizard:
            return "fail", _("Wizard was not created.")

        safe_journal = self._find_safe_manual_journal(wizard.currency_id)
        if safe_journal and wizard.journal_id != safe_journal:
            wizard.journal_id = safe_journal.id
            if hasattr(wizard, "_onchange_journal"):
                wizard._onchange_journal()

        manual_line = wizard.journal_id.inbound_payment_method_line_ids.filtered(lambda line: line.payment_method_id.code == "manual")[:1]
        if not manual_line:
            return "skip", _("Manual payment method is missing on selected journal.")

        wizard.payment_method_line_id = manual_line.id
        context = (action or {}).get("context") if isinstance(action, dict) else {}
        wizard.with_context(**(context or {})).action_create_payments()

        group_payment.invalidate_recordset(["generated_payment_ids", "state", "payer_partner_id"])
        payment = self.env["account.payment"].search(
            [("id", "in", group_payment.generated_payment_ids.ids)],
            order="id desc",
            limit=1,
        )
        if not payment:
            payment = self.env["account.payment"].search(
                [
                    ("ref", "=", move.name),
                    ("partner_id", "=", group_payment.payer_partner_id.id),
                ],
                order="id desc",
                limit=1,
            )

        expected = group_payment.payer_partner_id.id
        actual = payment.partner_id.id if payment else False
        ok = bool(payment and expected == actual)
        return ("pass" if ok else "fail", "expected=%s actual=%s payment_id=%s" % (expected, actual, payment.id if payment else False))


class QaAccountTestRunLine(models.Model):
    _name = "qa.account.test.run.line"
    _description = "Accounting Test Run Line"
    _order = "run_id desc, sequence asc, id asc"

    run_id = fields.Many2one("qa.account.test.run", required=True, ondelete="cascade")
    sequence = fields.Integer(required=True)
    case_code = fields.Char(required=True)
    case_name = fields.Char(required=True)
    status = fields.Selection(
        [
            ("pass", "PASS"),
            ("fail", "FAIL"),
            ("skip", "SKIP"),
        ],
        required=True,
    )
    message = fields.Text()
    duration_ms = fields.Integer(string="Duration (ms)")
