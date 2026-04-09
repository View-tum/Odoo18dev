# -*- coding: utf-8 -*-
from odoo import models, fields, api, Command


class AccountAgedReceiveableExtension(models.TransientModel):
    _name = "account.aged.receiveable.extension"
    _description = "Account Aged Receiveable Extension"

    name = fields.Char(string="Report Name", default="รายงานอายุลูกหนี้", readonly=True)
    route_id = fields.Many2one(
        comodel_name="delivery.route",
        string="สาย",
        help="(365 custom) เลือกสายการส่งเพื่อกรองลูกค้าในเขตที่เกี่ยวข้อง",
    )
    subregion_ids = fields.Many2many(
        comodel_name="delivery.sub.region",
        domain="[('route_id', '=', route_id)]",
        string="เขต",
        help="(365 custom) เลือกเขตการส่งเพื่อกรองลูกค้าในเขตที่เกี่ยวข้อง",
    )
    team_id = fields.Many2one(
        comodel_name="crm.team",
        string="ทีมขาย",
        help="(365 custom) เลือกทีมขายเพื่อกรองรายชื่อพนักงาน",
    )
    salesperson_ids = fields.Many2many(
        comodel_name="res.users",
        string="พนักงานขาย",
        domain="[('sale_team_id', '=', team_id), ('share', '=', False)] if team_id else []",
        help="(365 custom) เลือกพนักงานขายเพื่อกรองข้อมูลเอกสาร",
    )
    customer_ids = fields.Many2many(
        comodel_name="res.partner",
        domain="[('customer_rank', '>', 0)]",
        string="ลูกค้า",
        help="(365 custom) เลือกลูกค้าที่ต้องการดูรายงาน (สามารถเลือกได้หลายคน)",
    )
    payment_term_extension = fields.Selection(
        selection=[
            ("Payment Term Default", "เงื่อนไขการชำระเงินแบบปกติ"),
        ],
        string="เลือกเงื่อนไขการชำระเงิน",
        default="Payment Term Default",
        help="(365 custom) ตัวกรองเงื่อนไขการชำระเงิน (Default คือแบบปกติ)",
    )
    date_at = fields.Date(
        string="ณ วันที่",
        required=True,
        default=fields.Date.context_today,
        help="(365 custom) วันที่ที่ต้องการดูข้อมูลยอดหนี้คงค้าง",
    )
    date_type = fields.Selection(
        selection=[("date_maturity", "วันครบกำหนด"), ("invoice_date", "วันที่ใบแจ้งหนี้")],
        string="ประเภทวันที่",
        default="date_maturity",
        required=True,
        help="(365 custom) ฐานข้อมูลการคำนวณอายุหนี้: ตามวันครบกำหนด หรือ ตามวันที่ใบแจ้งหนี้",
    )
    target_move = fields.Selection(
        selection=[
            ("overdue", "เฉพาะยอดค้างชำระ"),
            ("all", "ทั้งหมด"),
        ],
        string="การกรองยอดค้างชำระ",
        default="overdue",
        required=True,
        help="(365 custom) เลือกการกรอง: เฉพาะยอดค้างชำระ (วันครบกำหนดน้อยกว่าหรือเท่ากับวันที่เลือก) / ทั้งหมด (รวมทั้งที่ยังไม่ถึงกำหนดชำระ)",
    )
    line_ids = fields.One2many(
        comodel_name="account.aged.receiveable.extension.line",
        inverse_name="wizard_id",
        string="Report Lines",
    )

    @api.onchange("route_id")
    def _onchange_route_id(self):
        """
        TH: เมื่อเปลี่ยนสายการส่ง ให้ทำการล้างค่าพื้นที่ย่อยที่เลือกไว้
        EN: Clear selected subregions when the delivery route is changed.
        """
        self.subregion_ids = [Command.clear()]

    @api.onchange("team_id")
    def _onchange_team_id(self):
        """
        TH: เมื่อเปลี่ยนทีมขาย ให้ทำการล้างค่าพนักงานขายที่เลือกไว้
        EN: Clear selected salesperson when the team is changed.
        """
        self.salesperson_ids = [Command.clear()]

    def _get_data(self):
        """
        TH: ดึงข้อมูลลูกหนี้คงค้างพื้นฐานจากฐานข้อมูล (Core Logic) โดยไม่มีเงื่อนไขเพิ่มเติมของ Sales หรือ PPS
        EN: Retrieve basic aged receivable data from the database (Core Logic) without additional Sales or PPS conditions.
        """
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
            "am.state = 'posted'",
        ]

        if self.target_move == "overdue":
            date_field = (
                "aml.date_maturity"
                if self.date_type == "date_maturity"
                else "am.invoice_date"
            )
            domain.append(f"{date_field} <= %(date_at)s")

        if self.subregion_ids:
            domain.append("p.subregion_id IN %(subregion_ids)s")
            params["subregion_ids"] = tuple(self.subregion_ids.ids)

        # if self.salesperson_id:
        #     domain.append(
        #         "(am.invoice_user_id = %(salesperson_id)s OR p.user_id = %(salesperson_id)s)"
        #     )
        #     params["salesperson_id"] = self.salesperson_id.id
        if self.salesperson_ids:
            domain.append(
                "(am.invoice_user_id IN %(salesperson_ids)s OR p.user_id IN %(salesperson_ids)s)"
            )
            params["salesperson_ids"] = tuple(self.salesperson_ids.ids)

        if self.customer_ids:
            domain.append("am.partner_id IN %(partner_ids)s")
            params["partner_ids"] = tuple(self.customer_ids.ids)

        base_date_field = (
            "aml.date_maturity"
            if self.date_type == "date_maturity"
            else "am.invoice_date"
        )
        adjusted_date_expression = base_date_field

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
                -- (SELECT so.id FROM sale_order so WHERE so.name = am.invoice_origin LIMIT 1) as sale_order_id,
                am.invoice_user_id as salesperson_id,
                am.partner_id,
                p.ref as partner_ref,
                p.name as partner_name,
                am.invoice_date,
                -- am.invoice_payment_term_id,
                COALESCE(am.invoice_payment_term_id, p_apt.id) as effective_payment_term_id,
                so.id as sale_order_id,
                so.name as sale_order_name,
                sp_p.name as salesperson_name,
                -- apt.name as payment_term_name,
                COALESCE(apt.name, p_apt.name) as payment_term_name,
                aml.date_maturity,
                
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
            LEFT JOIN sale_order so ON so.name = am.invoice_origin
            LEFT JOIN res_users sp ON sp.id = am.invoice_user_id
            LEFT JOIN res_partner sp_p ON sp_p.id = sp.partner_id
            JOIN res_partner p ON am.partner_id = p.id
            JOIN res_currency cur ON am.currency_id = cur.id
            LEFT JOIN account_payment_term apt ON am.invoice_payment_term_id = apt.id
            LEFT JOIN account_payment_term p_apt ON (p.property_payment_term_id ->> %(company_id)s::text)::int = p_apt.id
            
            WHERE {' AND '.join(domain)}
            ORDER BY days_overdue DESC, am.invoice_date ASC
        """

        self.env.cr.execute(sql_query, params)
        return self.env.cr.dictfetchall()

    def action_preview(self):
        """
        TH: สร้างข้อมูลบรรทัดรายงานพื้นฐานสำหรับแสดงผลบนหน้าจอ
        EN: Create basic report line items for on-screen display.
        """
        self.ensure_one()
        self.line_ids.unlink()

        results = self._get_data()

        if not results:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "ไม่พบข้อมูล",
                    "message": "ไม่มีใบแจ้งหนี้ค้างชำระ",
                    "type": "warning",
                    "sticky": False,
                },
            }

        lines_values = [
            Command.create(
                {
                    "invoice_id": res["invoice_id"],
                    "sale_order_id": res["sale_order_id"],
                    "salesperson_id": res["salesperson_id"],
                    "partner_ref": res["partner_ref"],
                    "partner_id": res["partner_id"],
                    "invoice_date": res["invoice_date"],
                    # "payment_term_id": res["invoice_payment_term_id"],
                    "payment_term_id": res["effective_payment_term_id"],
                    "currency_id": res["currency_id"],
                    "invoice_currency_id": res["invoice_currency_id"],
                    "date_maturity": res["date_maturity"],
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

    def action_export_excel(self):
        """
        TH: สร้างและดาวน์โหลดรายงานในรูปแบบไฟล์ Excel
        EN: Generate and download the report as an Excel file.
        """
        self.ensure_one()

        results = self._get_data()

        if not results:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "ไม่มีข้อมูล",
                    "message": "ไม่มีข้อมูลที่จะส่งออก",
                    "type": "warning",
                    "sticky": False,
                },
            }

        return self.env["account.aged.receiveable.export.xlsx"].generate_excel(
            self, results
        )
