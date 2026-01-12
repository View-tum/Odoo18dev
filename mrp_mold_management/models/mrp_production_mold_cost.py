# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

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

    def button_mark_done(self):
        # คำนวณค่า Mold Cost ให้เสร็จก่อนปิดงาน
        for mo in self:
            mo.workorder_ids._compute_mold_cost()
            mo._compute_mold_cost_total()

        res = super().button_mark_done()

        # สร้าง Journal + Valuation หลังจากปิดงานสำเร็จ
        self._create_mold_cost_move()
        return res
