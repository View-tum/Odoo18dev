# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    mold_cost_total = fields.Float(
        string="Total Mold Cost",
        compute="_compute_mold_cost_total",
        store=True,
    )
    mold_move_id = fields.Many2one(
        "account.move",
        string="Mold Journal Entry",
        readonly=True,
        copy=False,
    )

    def _get_busy_machine_ids(self, exclude_mo_id=False):
        domain = [
            ("state", "in", ("ready", "progress")),
        ]
        if exclude_mo_id:
            domain.append(("production_id", "!=", exclude_mo_id))
        busy_wos = self.env["mrp.workorder"].search(domain)
        return set(busy_wos.mapped("workcenter_id").ids)

    def _get_best_matrix_line(self, product_id, busy_machine_ids=None):
        matrix_lines = self.env["mrp.mold.matrix.report"].search([
            ("product_id", "=", product_id),
        ])
        if not matrix_lines:
            return False

        if busy_machine_ids is None:
            busy_machine_ids = set()

        healthy = matrix_lines.filtered(lambda ml: ml.mold_state != 'full')
        candidates = healthy or matrix_lines

        normal_first = candidates.filtered(lambda ml: ml.mold_state == 'normal')
        if normal_first:
            candidates = normal_first

        def _sort_key(line):
            busy = 1 if line.machine_id.id in busy_machine_ids else 0
            return (busy, -line.units_per_hour)

        return min(candidates, key=_sort_key)

    def action_suggest_machine_mold(self):
        self.ensure_one()
        if not self.env['mrp.workcenter'].is_mold_management_enabled():
            return

        try:
            busy_ids = self._get_busy_machine_ids(exclude_mo_id=self.id)
        except Exception:
            busy_ids = set()

        suggestions = []
        for wo in self.workorder_ids:
            if wo.state in ('done', 'cancel') or not wo.product_id:
                continue

            try:
                best = self._get_best_matrix_line(wo.product_id.id, busy_machine_ids=busy_ids)
            except Exception:
                continue

            if not best:
                continue

            if best.machine_id.id != wo.workcenter_id.id:
                busy_tag = " [BUSY]" if best.machine_id.id in busy_ids else ""
                wo.workcenter_id = best.machine_id.id
                suggestions.append(
                    f"{wo.name}: {best.machine_id.name} + {best.mold_id.name} "
                    f"({best.units_per_hour:.0f} pcs/hr, {best.mold_state}{busy_tag})"
                )

        if suggestions:
            try:
                body = _("<b>Auto Mold Selection:</b><br/>%s") % "<br/>".join(suggestions)
                self.message_post(body=body)
            except Exception:
                pass



    @api.depends("workorder_ids.mold_cost")
    def _compute_mold_cost_total(self):
        for mo in self:
            mo.mold_cost_total = sum(mo.workorder_ids.mapped("mold_cost"))

    def _get_mold_accounts_and_journal(self):
        AccountJournal = self.env["account.journal"]
        for mo in self:
            mold_with_account = mo.workorder_ids.mapped("mold_ids").filtered("expense_account_id")
            expense_account = mold_with_account[:1].expense_account_id if mold_with_account else False

            debit_account = (
                mo.product_id.categ_id.property_stock_valuation_account_id
                or mo.product_id.categ_id.property_stock_account_output_categ_id
            )

            journal = AccountJournal.search(
                [("code", "=", "STJ"), ("company_id", "=", mo.company_id.id)],
                limit=1,
            )
            if not journal:
                journal = AccountJournal.search(
                    [("type", "=", "general"), ("company_id", "=", mo.company_id.id)],
                    limit=1,
                )

            yield mo, expense_account, debit_account, journal

    def _create_mold_cost_move(self):
        Move = self.env["account.move"]
        ValuationLayer = self.env["stock.valuation.layer"]

        for mo, expense_account, debit_account, journal in self._get_mold_accounts_and_journal():
            if mo.mold_move_id or not mo.mold_cost_total:
                continue

            if not expense_account or not debit_account or not journal:
                continue

            all_molds = mo.workorder_ids.mapped("mold_ids")
            mold_names = ", ".join(sorted(list(set(all_molds.mapped("name")))))
            ref_name = f"{mo.name} - {mold_names}" if mold_names else mo.name

            amount = mo.mold_cost_total

            # หา finished_move ก่อน เพื่อป้องกันการลงบัญชีแต่ไม่มีของให้เพิ่มมูลค่า
            finished_move = mo.move_finished_ids.filtered(
                lambda m: m.state == 'done' and m.product_id == mo.product_id
            )[:1]

            # ถ้าไม่เจอ move ที่เสร็จแล้ว (อาจจะเพราะเพิ่งกด done) ให้หาอันที่ state ไม่ใช่ cancel
            if not finished_move:
                finished_move = mo.move_finished_ids.filtered(
                    lambda m: m.state != 'cancel' and m.product_id == mo.product_id
                )[:1]

            if not finished_move:
                continue

            # 1. สร้าง Journal Entry
            move_vals = {
                "journal_id": journal.id,
                "date": fields.Date.context_today(mo),
                "ref": ref_name,
                "line_ids": [
                    (0, 0, {
                        "name": ref_name,
                        "account_id": debit_account.id,
                        "debit": amount,
                        "credit": 0.0,
                    }),
                    (0, 0, {
                        "name": ref_name,
                        "account_id": expense_account.id,
                        "debit": 0.0,
                        "credit": amount,
                    }),
                ],
            }
            move = Move.create(move_vals)
            move.action_post()
            mo.mold_move_id = move.id

            # 2. สร้าง Stock Valuation Layer
            ValuationLayer.sudo().create({
                    'company_id': mo.company_id.id,
                    'product_id': mo.product_id.id,
                    'stock_move_id': finished_move.id,
                    'account_move_id': move.id,
                    'quantity': 0,
                    'value': amount,
                    'description': ref_name,
                })

    def action_confirm(self):
        if self.env['mrp.workcenter'].is_mold_management_enabled() and not self.env.context.get('skip_mold_check'):
            for mo in self:
                wo_without_mold = mo.workorder_ids.filtered(
                    lambda w: w.state not in ('done', 'cancel') and not w.mold_ids and w.product_id
                )
                if wo_without_mold:
                    mo.action_suggest_machine_mold()

                full_molds = mo.workorder_ids.mapped('mold_ids').filtered(lambda m: m.mold_state == 'full')
                if full_molds:
                    mold_names = ", ".join(full_molds.mapped('name'))
                    msg = _(
                        "The following molds have reached their life limit (Full): %s. "
                        "Continuing may affect production quality. "
                        "Do you want to proceed anyway or select an alternative?"
                    ) % mold_names

                    return {
                        "name": _("Mold Life Warning"),
                        "type": "ir.actions.act_window",
                        "res_model": "mrp.mold.warning.wizard",
                        "view_mode": "form",
                        "target": "new",
                        "context": {
                            "default_production_id": mo.id,
                            "default_message": msg,
                        },
                    }
        return super().action_confirm()

    def button_mark_done(self):
        # คำนวณค่า Mold Cost ให้เสร็จก่อนปิดงาน
        for mo in self:
            mo.workorder_ids._compute_mold_cost()
            mo._compute_mold_cost_total()

        res = super().button_mark_done()

        # สร้าง Journal + Valuation หลังจากปิดงานสำเร็จ
        self._create_mold_cost_move()
        return res
