# -*- coding: utf-8 -*-
from odoo import models, fields, api, Command
from dateutil.relativedelta import relativedelta
from datetime import datetime, time


class AccountCommissionManagement(models.TransientModel):
    _name = "account.commission.management"
    _description = "Account Commission Management"

    name = fields.Char(
        string="Report Name",
        compute="_compute_name",
    )
    team_id = fields.Many2one(
        comodel_name="crm.team",
        string="ทีมขาย",
        help="(365 custom) เลือกทีมขายเพื่อกรองพนักงานขายในรายงาน หากไม่เลือกจะรวมทุกทีมขาย",
    )
    salesperson_ids = fields.Many2many(
        comodel_name="res.users",
        string="พนักงานขาย",
        domain="[('sale_team_id', '=', team_id), ('share', '=', False)] if team_id else []",
        help="(365 custom) เลือกพนักงานขายเฉพาะเพื่อรวมในรายงาน หากไม่เลือกจะรวมทุกพนักงานขาย",
    )
    date_from = fields.Date(
        string="ตั้งแต่วันที่",
        help="(365 custom) วันเริ่มต้นของช่วงข้อมูลในรายงาน (รวมวันนั้นด้วย) หากไม่ระบุจะใช้วันที่ 1 ของเดือนปัจจุบัน",
    )
    date_to = fields.Date(string="ถึงวันที่", help="(365 custom) วันสิ้นสุดของช่วงข้อมูลในรายงาน")
    report_id = fields.Many2one(
        comodel_name="jasper.report",
        domain=[("model_id", "=", _name)],
        string="รายงาน",
        help="(365 custom) เลือกแบบฟอร์มรายงานที่ต้องการใช้สำหรับพิมพ์รายงาน หากไม่เลือกจะใช้แบบฟอร์มเริ่มต้นตามการตั้งค่า",
    )
    line_ids = fields.One2many(
        comodel_name="account.commission.management.line",
        inverse_name="account_commission_id",
        string="Commission Lines",
    )

    @api.model
    def default_get(self, fields_list):
        """
        This method is executed every time the Wizard is opened (Target: new).
        We use this opportunity to delete old Line data for that user.
        """

        res = super(AccountCommissionManagement, self).default_get(fields_list)

        if "team_id" in fields_list and not res.get("team_id"):
            team_id = self.env["crm.team"].search([], limit=1, order="id asc")
            res["team_id"] = team_id.id if team_id else False

        if "date_from" in fields_list and not res.get("date_from"):
            res["date_from"] = fields.Date.context_today(self).replace(day=1)
        if "date_to" in fields_list and not res.get("date_to"):
            res["date_to"] = fields.Date.context_today(self)

        if "report_id" in fields_list and not res.get("report_id"):
            default_report = self.env["jasper.report"].search(
                [("model_id", "=", self._name)], limit=1, order="id asc"
            )
            res["report_id"] = default_report.id if default_report else False

        return res

    @api.onchange("team_id")
    def _onchange_team_id(self):
        """เมื่อเปลี่ยนทีมขาย ให้ล้างค่าพนักงานขายที่เคยเลือกไว้"""
        if self.team_id:
            self.salesperson_ids = [Command.clear()]

    def _get_so_exchange_rate(self, so):
        """
        ฟังก์ชันช่วยคำนวณอัตราแลกเปลี่ยนของ Sale Order ใบนั้นๆ
        Return: อัตราแลกเปลี่ยน (Float) เพื่อแปลงเป็น THB (Company Currency)
        """
        company_currency = self.env.company.currency_id
        so_currency = so.currency_id
        so_date = so.date_order or fields.Date.context_today(self)

        if so_currency == company_currency:
            return 1.0
        if getattr(so, "sale_manual_currency_rate", False):
            return so.sale_manual_currency_rate
        return so_currency._get_conversion_rate(
            so_currency, company_currency, self.env.company, so_date
        )

    def _get_commission_data(self, salesperson_id):
        """
        - เน้น Transaction จริง (Invoice/Payment) ในช่วงเวลา
        - กรองเฉพาะที่มี SO
        - แยกบรรทัด (1 Inv = 1 Line) เพื่อความชัดเจนในการจ่าย
        """
        commission_data = []

        # เตรียม Config Commission
        commission_rate = 0.0
        commission_trigger_type = False

        if salesperson_id.salesregion_id:
            commission_rule = self.env["account.commission.rule"].search(
                [("region_ids", "in", salesperson_id.salesregion_id.id)], limit=1
            )
            if commission_rule and commission_rule.rate_id:
                commission_rate = commission_rule.rate_id.value
                commission_trigger_type = commission_rule.commission_trigger

        # --- PATH A: Sale กรุงเทพ (Trigger: Invoice Confirm) ---
        if commission_trigger_type == "invoice_confirmed":
            move_domain = [
                ("move_type", "in", ["out_invoice", "out_refund"]),
                ("state", "=", "posted"),
                ("invoice_date", ">=", self.date_from),
                ("invoice_date", "<=", self.date_to),
                ("invoice_user_id", "=", salesperson_id.id),
            ]
            moves = self.env["account.move"].search(move_domain)

            for move in moves:
                so = move.invoice_line_ids.sale_line_ids.order_id
                print(f"DEBUG: Move {move.name} linked SO: {[s.name for s in so]}")
                if not so:
                    continue
                so = so[0]

                exchange_rate = self._get_so_exchange_rate(so)
                amount_thb = move.amount_total * exchange_rate

                is_refund = move.move_type == "out_refund"
                if is_refund:
                    amount_thb = -abs(amount_thb)

                # Calc Commission
                amount_commission = amount_thb * (commission_rate / 100.0)
                payment_val = 0.0
                if move.amount_total and move.amount_total != 0:
                    ratio = (
                        move.amount_total - move.amount_residual
                    ) / move.amount_total
                    payment_val = amount_thb * ratio

                commission_data.append(
                    {
                        "account_move_id": move.id,
                        "salesperson_id": salesperson_id.id,
                        "customer_code": move.partner_id.ref,
                        "customer_name": move.partner_id.name,
                        "sale_order_name": so.name if so else "",
                        "invoice_date": move.invoice_date,
                        "invoice_name": move.name if not is_refund else "",
                        "credit_note_name": move.name if is_refund else "",
                        "amount_invoice_total": (amount_thb if not is_refund else 0.0),
                        "amount_credit_note_total": amount_thb if is_refund else 0.0,
                        "amount_payment_total": payment_val,
                        "amount_commission_total": amount_commission,
                    }
                )

        # --- PATH B: Sale ต่างจังหวัด (Trigger: Payment/Paid) ---
        elif commission_trigger_type == "invoice_paid":
            reconcile_domain = [
                ("max_date", ">=", self.date_from),
                ("max_date", "<=", self.date_to),
                "|",
                # Case 1: จ่ายชำระ Invoice (De: Inv, Cr: Bank, Cash)
                "&",
                "&",
                "&",
                ("debit_move_id.move_id.move_type", "=", "out_invoice"),
                ("debit_move_id.move_id.invoice_user_id", "=", salesperson_id.id),
                ("credit_move_id.journal_id.type", "in", ["bank", "cash"]),
                ("debit_move_id.move_id.state", "=", "posted"),
                # Case 2: จ่ายคืน Refund/CN (Cr: CN, De: Bank, Cash)
                "&",
                "&",
                "&",
                ("credit_move_id.move_id.move_type", "=", "out_refund"),
                ("credit_move_id.move_id.invoice_user_id", "=", salesperson_id.id),
                ("debit_move_id.journal_id.type", "in", ["bank", "cash"]),
                ("credit_move_id.move_id.state", "=", "posted"),
            ]
            partials = self.env["account.partial.reconcile"].search(reconcile_domain)

            for partial in partials:
                # ตรวจสอบว่าเป็นเคส รับชำระ หรือ คืนเงิน
                if partial.debit_move_id.move_id.move_type == "out_invoice":
                    # --- Case 1: รับชำระ Invoice ---
                    move = partial.debit_move_id.move_id  # Invoice
                    account_move_invoice_name = move.name
                    account_move_cn_name = ""
                    sign = 1.0
                else:
                    # --- Case 2: จ่ายคืน Refund (CN) ---
                    move = partial.credit_move_id.move_id  # Credit Note
                    account_move_invoice_name = ""
                    account_move_cn_name = move.name
                    sign = -1.0

                # [Rule] ต้องมี SO เท่านั้น
                so = move.invoice_line_ids.sale_line_ids.order_id
                if not so:
                    continue
                so = so[0]

                exchange_rate = self._get_so_exchange_rate(so)

                # 1. ยอดที่รับชำระ/จ่ายคืนจริง (Collection)
                paid_amount_thb = partial.amount * exchange_rate
                if sign < 0:
                    paid_amount_thb = -abs(paid_amount_thb)
                # 2. Commission
                amount_commission = paid_amount_thb * (commission_rate / 100.0)

                commission_data.append(
                    {
                        "account_move_id": move.id,
                        "salesperson_id": salesperson_id.id,
                        "customer_code": move.partner_id.ref,
                        "customer_name": move.partner_id.name,
                        "sale_order_name": so.name if so else "",
                        "invoice_date": move.invoice_date,
                        "invoice_name": account_move_invoice_name,
                        "credit_note_name": account_move_cn_name,
                        "amount_invoice_total": paid_amount_thb if sign > 0 else 0.0,
                        "amount_credit_note_total": (
                            paid_amount_thb if sign < 0 else 0.0
                        ),
                        "amount_payment_total": paid_amount_thb,
                        "amount_commission_total": amount_commission,
                    }
                )

        return commission_data

    def _compute_name(self):
        date_str = fields.Date.today().strftime("%Y-%m-%d")
        report_name = f"รายงานคอมมิชชั่น - {date_str}"
        self.name = report_name

    def _get_report_filename(self):
        self.ensure_one()
        date_str = fields.Date.today().strftime("%Y-%m-%d")
        report_name = f"รายงานคอมมิชชั่น - {date_str}"
        return report_name

    def _get_report_data(self):
        self.ensure_one()
        all_report_data = []

        for salesperson in self.salesperson_ids:
            report_data = self._get_commission_data(salesperson)
            all_report_data.extend(report_data)

        return all_report_data

    def action_jasper(self):
        self.ensure_one()

        if not self.report_id:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "การตั้งค่าไม่ถูกต้อง",
                    "message": "  • ไม่พบรายงาน Jasper Report กรุณาตรวจสอบการตั้งค่า",
                    "type": "danger",
                    "sticky": False,
                },
            }

        salesperson_ids = (
            ",".join(map(str, self.salesperson_ids.ids))
            if self.salesperson_ids
            else None
        )
        date_from = self.date_from.strftime("%Y-%m-%d") if self.date_from else None
        date_to = self.date_to.strftime("%Y-%m-%d") if self.date_to else None
        account_commission_id = str(self.id) if self.id else None

        data = {
            "salesperson_ids": salesperson_ids,
            "date_from": date_from,
            "date_to": date_to,
            "account_commission_id": account_commission_id,
        }

        return self.report_id.run_report(docids=[self.ids[0]], data=data)

    def action_compute_lines(self):
        self.ensure_one()
        if self.date_from and self.date_to and self.date_from > self.date_to:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "วันที่ไม่ถูกต้อง",
                    "message": "  • วันที่เริ่มต้น ต้องมาก่อน หรือวันเดียวกับ วันที่สิ้นสุด",
                    "type": "danger",
                    "sticky": False,
                },
            }

        self.line_ids.unlink()

        all_data = self._get_report_data()
        lines = []

        for item in all_data:
            lines.append(
                Command.create(
                    {
                        "salesperson_id": item.get("salesperson_id") or False,
                        "customer_code": item.get("customer_code") or "",
                        "customer_name": item.get("customer_name") or "",
                        "sale_order_name": item.get("sale_order_name", ""),
                        "invoice_date": item.get("invoice_date") or False,
                        "invoice_name": item.get("invoice_name") or "",
                        "credit_note_name": item.get("credit_note_name") or "",
                        "amount_invoice_total": item.get("amount_invoice_total", 0.0),
                        "amount_payment_total": item.get("amount_payment_total", 0.0),
                        "amount_credit_note_total": item.get(
                            "amount_credit_note_total", 0.0
                        ),
                        "amount_commission": item.get("amount_commission_total", 0.0),
                    }
                )
            )

        self.write({"line_ids": [Command.clear()] + lines})

        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_export_excel(self):
        self.ensure_one()
        report_xml_id = False
        report_xml_id = "account_commission_management.action_report_commission_excel"

        if not report_xml_id:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "การตั้งค่าไม่ถูกต้อง",
                    "message": "  • ไม่มีรายงานที่ถูกต้อง โปรดตรวจสอบการตั้งค่า",
                    "type": "danger",
                    "sticky": False,
                },
            }

        return self.env.ref(report_xml_id).report_action(self)
