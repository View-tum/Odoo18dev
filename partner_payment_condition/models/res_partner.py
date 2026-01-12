# -*- coding: utf-8 -*-
import calendar
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = "res.partner"

    payment_extra_days = fields.Integer(
        string="จำนวนวันผ่อนผันเพิ่มเติม (+วัน)",
        help="(365 custom) จำนวนวันที่ให้เลื่อนวันครบกำหนดเพิ่มเติมจากวันที่คำนวณได้.",
        default=0,
    )
    collect_on_day_enabled = fields.Boolean(
        string="ใช้การตัดรอบตามวันที่กำหนด",
        help="(365 custom) เปิดใช้งานเพื่อให้ระบบกำหนดวันครบกำหนดเป็นวันที่เดียวกันของทุกเดือน.",
    )
    collect_on_day = fields.Integer(
        string="ตัดรอบในวันที่ (1-31)",
        help="(365 custom) ระบุวันที่ต้องการให้ครบกำหนด หากเดือนนั้นไม่มีวันดังกล่าวระบบจะใช้วันสุดท้ายของเดือน.",
    )
    notify_sales_on_overdue = fields.Boolean(
        string="แจ้งเตือนเซลส์เมื่อเลยกำหนด",
        default=True,
        help="(365 custom) ถ้าเปิดไว้ระบบจะสร้างกิจกรรมแจ้งเตือนให้ผู้รับผิดชอบเมื่อใบแจ้งหนี้ค้างชำระ.",
    )

    @api.constrains("collect_on_day", "collect_on_day_enabled")
    def _check_collect_on_day(self):
        for partner in self:
            if partner.collect_on_day_enabled:
                day = partner.collect_on_day or 0
                if not 1 <= day <= 31:
                    raise UserError(_("กรุณากรอกวันที่ตัดรอบระหว่าง 1 ถึง 31"))


class AccountMove(models.Model):
    _inherit = "account.move"

    def _ppc_compute_adjusted_due_date(self, base_due):
        """คำนวณวันครบกำหนดตามเงื่อนไขของคู่ค้าหรือรายการราคา"""
        self.ensure_one()
        partner = self.partner_id.commercial_partner_id

        collect_enabled = partner.collect_on_day_enabled
        collect_day = partner.collect_on_day
        extra_days = partner.payment_extra_days

        pricelist = partner.property_product_pricelist
        if pricelist and pricelist.ppc_override:
            collect_enabled = pricelist.ppc_collect_on_day_enabled
            collect_day = pricelist.ppc_collect_on_day
            extra_days = pricelist.ppc_payment_extra_days

        new_due = base_due

        if collect_enabled and collect_day:
            day_target = max(1, min(collect_day, 31))

            def _adjusted(year, month):
                last_day = calendar.monthrange(year, month)[1]
                actual_day = min(day_target, last_day)
                return date(year, month, actual_day), actual_day

            candidate, candidate_day = _adjusted(base_due.year, base_due.month)
            if base_due.day <= candidate_day:
                new_due = candidate
            else:
                next_month = date(base_due.year, base_due.month,
                                  1) + relativedelta(months=1)
                new_due, _candidate_day = _adjusted(
                    next_month.year, next_month.month)

        if extra_days:
            new_due = new_due + timedelta(days=extra_days)

        return new_due

    def action_post(self):
        """หลังโพสต์ใบแจ้งหนี้ ปรับวันครบกำหนดตามเงื่อนไขที่ตั้งไว้"""
        res = super().action_post()
        for inv in self.filtered(lambda m: m.move_type in ("out_invoice", "out_refund")):
            partner = inv.partner_id.commercial_partner_id
            pricelist = partner.property_product_pricelist
            has_partner_rules = partner.payment_extra_days or partner.collect_on_day_enabled
            has_pricelist_rules = pricelist and pricelist.ppc_override and (
                pricelist.ppc_payment_extra_days or pricelist.ppc_collect_on_day_enabled
            )
            if not (has_partner_rules or has_pricelist_rules):
                continue

            base_due = inv.invoice_date_due or inv.invoice_date or fields.Date.today()
            adjusted = inv._ppc_compute_adjusted_due_date(base_due)
            inv.write({"invoice_date_due": adjusted})
        return res

    @api.model
    def _ppc_cron_notify_overdue(self):
        """Cron สร้างกิจกรรมแจ้งเตือนใบแจ้งหนี้ค้างชำระสำหรับทีมขาย"""
        today = fields.Date.context_today(self)
        domain = [
            ("move_type", "in", ("out_invoice", "out_refund")),
            ("state", "=", "posted"),
            ("payment_state", "in", ("not_paid", "partial")),
            ("invoice_date_due", "<", today),
            ("partner_id.commercial_partner_id.notify_sales_on_overdue", "=", True),
        ]
        invoices = self.search(domain, limit=500)
        if not invoices:
            return

        todo_type = self.env.ref("mail.mail_activity_data_todo")

        summary = _("Overdue: ใบแจ้งหนี้ค้างชำระ")

        for inv in invoices:
            user = (
                inv.invoice_user_id
                or inv.partner_id.user_id
                or getattr(inv.company_id, "user_id", False)
                or self.env.user
            )
            existing = self.env["mail.activity"].search(
                [
                    ("res_model", "=", inv._name),
                    ("res_id", "=", inv.id),
                    ("activity_type_id", "=", todo_type.id),
                    ("summary", "=", summary),
                    ("date_deadline", ">=", today - timedelta(days=1)),
                ],
                limit=1,
            )
            if existing:
                continue

            note = _(
                "ลูกค้า: %(partner)s\n"
                "เอกสาร: %(name)s\n"
                "ครบกำหนด: %(due)s\n"
                "ยอดค้างชำระ: %(amount).2f\n\n"
                "โปรดติดตามและประสานงานกับลูกค้าเพื่อเร่งการชำระเงิน."
            ) % {
                "partner": inv.partner_id.display_name,
                "name": inv.name or inv.ref or inv.move_name or "",
                "due": inv.invoice_date_due and inv.invoice_date_due.strftime("%Y-%m-%d") or "",
                "amount": inv.amount_residual,
            }

            self.env["mail.activity"].create(
                {
                    "res_model_id": self.env["ir.model"]._get_id(inv._name),
                    "res_id": inv.id,
                    "activity_type_id": todo_type.id,
                    "summary": summary,
                    "user_id": user.id,
                    "note": note,
                    "date_deadline": today,
                }
            )
