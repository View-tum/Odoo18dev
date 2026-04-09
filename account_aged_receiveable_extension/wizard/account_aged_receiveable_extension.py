# -*- coding: utf-8 -*-
from odoo import models, fields, api, Command


class AccountAgedReceiveableExtension(models.TransientModel):
    _name = "account.aged.receiveable.extension"
    _description = "Account Aged Receiveable Extension"

    name = fields.Char(string="Report Name", default="รายงานอายุลูกหนี้", readonly=True)
    salesperson_id = fields.Many2one(
        comodel_name="res.users",
        string="Salespersons",
        domain=lambda self: self._get_salesperson_domain(),
        help="(365 custom) เลือกพนักงานขายเพื่อกรองข้อมูลเอกสาร",
    )
    customer_ids = fields.Many2many(
        comodel_name="res.partner",
        domain="[('customer_rank', '>', 0)]",
        string="Customers",
        help="(365 custom) เลือกลูกค้าที่ต้องการดูรายงาน (สามารถเลือกได้หลายคน)",
    )
    payment_term_extension = fields.Selection(
        selection=[
            ("Payment Term Default", "Payment Term Default"),
        ],
        string="Payment Term Filter",
        default="Payment Term Default",
        help="(365 custom) ตัวกรองเงื่อนไขการชำระเงิน (Default คือแบบปกติ)",
    )
    date_at = fields.Date(
        string="As of Date",
        required=True,
        default=fields.Date.context_today,
        help="(365 custom) วันที่ที่ต้องการดูข้อมูลยอดหนี้คงค้าง",
    )
    date_type = fields.Selection(
        selection=[("date_maturity", "Due Date"), ("invoice_date", "Invoice Date")],
        string="Ageing Based On",
        default="date_maturity",
        required=True,
        help="(365 custom) ฐานข้อมูลการคำนวณอายุหนี้: ตามวันครบกำหนด หรือ ตามวันที่ใบแจ้งหนี้",
    )
    target_move = fields.Selection(
        selection=[
            ("posted", "All Posted Entries"),
            ("all", "All Entries"),
        ],
        string="Target Moves",
        default="posted",
        required=True,
        help="(365 custom) เลือกสถานะเอกสาร: เฉพาะลงบัญชีแล้ว หรือ ทั้งหมด",
    )
    line_ids = fields.One2many(
        comodel_name="account.aged.receiveable.extension.line",
        inverse_name="wizard_id",
        string="Report Lines",
    )

    def _get_salesperson_domain(self):
        """
        TH: คืนค่า Domain สำหรับกรอง Salesperson ตามสิทธิ์ของผู้ใช้งาน
        EN: Return the domain to filter Salesperson based on user access rights.
        """
        group_xml_ids = [
            "sales_team.group_sale_salesman",
            "sales_team.group_sale_salesman_all_leads",
            "sales_team.group_sale_manager",
        ]
        sales_group_ids = []
        for xml_id in group_xml_ids:
            group = self.env.ref(xml_id, raise_if_not_found=False)
            if group:
                sales_group_ids.append(group.id)

        return [
            ("groups_id", "in", sales_group_ids),
            ("share", "=", False),
        ]

    @api.onchange("salesperson_id")
    def _onchange_salesperson_id(self):
        """
        TH: เมื่อเปลี่ยน Salesperson ให้ทำการล้างค่าลูกค้าที่เลือกไว้
        EN: Clear selected customers when the Salesperson is changed.
        """
        if self.salesperson_id:
            self.customer_ids = [Command.clear()]

    @api.onchange("customer_ids")
    def _onchange_customer_ids(self):
        """
        TH: เมื่อเลือกลูกค้า ให้ทำการล้างค่า Salesperson
        EN: Clear selected Salesperson when customers are selected.
        """
        if self.customer_ids:
            self.salesperson_id = False

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
                am.partner_id,
                p.name as partner_name,
                am.invoice_date,
                am.invoice_payment_term_id,
                apt.name as payment_term_name,
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
            JOIN res_partner p ON am.partner_id = p.id
            JOIN res_currency cur ON am.currency_id = cur.id
            LEFT JOIN account_payment_term apt ON am.invoice_payment_term_id = apt.id
            
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
                    "title": "No Records Found",
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
                    "message": "Please select Salesperson or Customer.",
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
                    "title": "No Data",
                    "message": "No records to export.",
                    "type": "warning",
                    "sticky": False,
                },
            }

        return self.env["account.aged.receiveable.export.xlsx"].generate_excel(
            self, results
        )
