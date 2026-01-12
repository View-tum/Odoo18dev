# -*- coding: utf-8 -*-
from odoo import models, fields, Command


class AccountAgedReceiveableExtension(models.TransientModel):
    _inherit = "account.aged.receiveable.extension"

    payment_term_extension = fields.Selection(
        selection_add=[
            ("Payment Term Sales", "Payment Term Sales"),
            ("Payment Term Customer", "Payment Term Customer"),
        ],
        ondelete={
            "Payment Term Sales": "set default",
            "Payment Term Customer": "set default",
        },
        help="(365 custom) เลือกเงื่อนไขเพิ่มเติม: Sales (แสดง Extra Days) หรือ Customer (แสดง Next Run)",
    )

    def _get_data(self):
        """
        TH: ดึงข้อมูลลูกหนี้และคำนวณวันครบกำหนดชำระตามเงื่อนไขที่เลือก (Sales/Customer)
            โดยมีการ Join ตารางเพิ่มเติมและคำนวณวัน Due Date ใหม่ตาม Logic
        EN: Retrieve receivable data and calculate due dates based on the selected condition (Sales/Customer),
            including joining additional tables and recalculating Due Date logic.
        """
        if self.payment_term_extension not in [
            "Payment Term Sales",
            "Payment Term Customer",
        ]:
            return super()._get_data()

        comp_currency_id = self.env.company.currency_id.id
        user_tz = self.env.user.tz or "UTC"

        params = {
            "company_id": self.env.company.id,
            "date_at": self.date_at,
            "comp_currency_id": comp_currency_id,
            "tz": user_tz,
        }

        domain = [
            "am.move_type = 'out_invoice'",
            "account.account_type = 'asset_receivable'",
            "am.company_id = %(company_id)s",
            "aml.amount_residual > 0",
        ]

        if self.target_move == "posted":
            domain.append("am.state = 'posted'")

        if self.salesperson_id:
            domain.append(
                "(am.invoice_user_id = %(salesperson_id)s OR p.user_id = %(salesperson_id)s)"
            )
            params["salesperson_id"] = self.salesperson_id.id

        if self.customer_ids:
            domain.append("am.partner_id IN %(partner_ids)s")
            params["partner_ids"] = tuple(self.customer_ids.ids)

        base_date_field = (
            "aml.date_maturity"
            if self.date_type == "date_maturity"
            else "am.invoice_date"
        )

        extra_days_sql = "0"
        adjusted_date_expression = base_date_field

        if self.payment_term_extension == "Payment Term Sales":
            extra_days_sql = "COALESCE(p.payment_extra_days, 0)"
            domain.append("COALESCE(p.payment_extra_days, 0) != 0")
            adjusted_date_expression = f"({base_date_field} + {extra_days_sql})"

        elif self.payment_term_extension == "Payment Term Customer":
            domain.append("ps.min_next_run IS NOT NULL")
            adjusted_date_expression = (
                "(ps.min_next_run AT TIME ZONE 'UTC' AT TIME ZONE %(tz)s)::date"
            )

        amount_field_sql = """
            CASE 
                WHEN am.currency_id != %(comp_currency_id)s AND COALESCE(aml.amount_residual_currency, 0) != 0
                THEN aml.amount_residual_currency 
                ELSE aml.amount_residual 
            END
        """

        sql_query = f"""
            SELECT 
                am.id as invoice_id,
                am.name as invoice_name,
                am.partner_id,
                p.name as partner_name,
                am.invoice_date,
                am.invoice_payment_term_id,
                apt.name as payment_term_name,
                aml.date_maturity,
                
                {extra_days_sql} as extra_days,
                
                ps.min_next_run::date as next_run_date,
                
                {amount_field_sql} as amount_residual,
                
                am.currency_id as invoice_currency_id,
                am.currency_id as currency_id,
                cur.name as currency_name,
                
                (%(date_at)s - {adjusted_date_expression}) as days_overdue,

                CASE WHEN (%(date_at)s - {adjusted_date_expression}) <= 0 
                     THEN {amount_field_sql} ELSE 0 END as amount_not_due,

                CASE WHEN (%(date_at)s - {adjusted_date_expression}) BETWEEN 1 AND 30 
                     THEN {amount_field_sql} ELSE 0 END as amount_1_30,

                CASE WHEN (%(date_at)s - {adjusted_date_expression}) BETWEEN 31 AND 60 
                     THEN {amount_field_sql} ELSE 0 END as amount_31_60,

                CASE WHEN (%(date_at)s - {adjusted_date_expression}) BETWEEN 61 AND 90 
                     THEN {amount_field_sql} ELSE 0 END as amount_61_90,

                CASE WHEN (%(date_at)s - {adjusted_date_expression}) > 90 
                     THEN {amount_field_sql} ELSE 0 END as amount_over_90
                     
            FROM account_move_line aml
            JOIN account_move am ON aml.move_id = am.id
            JOIN account_account account ON aml.account_id = account.id
            JOIN res_partner p ON am.partner_id = p.id
            JOIN res_currency cur ON am.currency_id = cur.id
            LEFT JOIN account_payment_term apt ON am.invoice_payment_term_id = apt.id
            
            LEFT JOIN (
                SELECT 
                    partner_id, 
                    MIN(next_run) as min_next_run
                FROM pps_schedule
                WHERE schedule_type = 'payment'
                GROUP BY partner_id
            ) ps ON ps.partner_id = p.id
            
            WHERE {' AND '.join(domain)}
            ORDER BY days_overdue DESC, am.invoice_date ASC
        """

        self.env.cr.execute(sql_query, params)
        return self.env.cr.dictfetchall()

    def action_preview(self):
        """
        TH: สร้างข้อมูลบรรทัดรายงานสำหรับแสดงผลบนหน้าจอ รองรับการ Map ค่า Extra Days และ Next Run
        EN: Create report line items for on-screen display, supporting Extra Days and Next Run mapping.
        """
        self.ensure_one()
        self.line_ids.unlink()

        results = self._get_data()

        if not results:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "No Records",
                    "message": "No invoices match criteria.",
                    "type": "warning",
                    "sticky": False,
                },
            }

        if not self.salesperson_id and not self.customer_ids:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Selection Required",
                    "message": "Select Salesperson or Customer.",
                    "type": "warning",
                    "sticky": False,
                },
            }

        lines_values = [
            Command.create(
                {
                    "invoice_id": res["invoice_id"],
                    "partner_id": res["partner_id"],
                    "invoice_date": res["invoice_date"],
                    "payment_term_id": res["invoice_payment_term_id"],
                    "currency_id": res["currency_id"],
                    "invoice_currency_id": res["invoice_currency_id"],
                    "date_maturity": res["date_maturity"],
                    "extra_days": res.get("extra_days", 0),
                    "next_run_date": res.get("next_run_date"),
                    "amount_not_due": res["amount_not_due"],
                    "amount_residual": res["amount_residual"],
                    "days_overdue": (
                        res["days_overdue"] if res["days_overdue"] > 0 else 0
                    ),
                    "amount_1_30": res["amount_1_30"],
                    "amount_31_60": res["amount_31_60"],
                    "amount_61_90": res["amount_61_90"],
                    "amount_over_90": res["amount_over_90"],
                }
            )
            for res in results
        ]

        self.line_ids = lines_values
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }
