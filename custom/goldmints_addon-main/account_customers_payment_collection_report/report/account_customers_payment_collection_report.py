# report/account_customers_payment_collection_report.py
# -*- coding: utf-8 -*-
import base64
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from .account_customers_payment_collection_xlsx import (
    AccountCustomerPaymentCollectionXlsx,
)


class AccountCustomersPaymentCollectionReport(models.TransientModel):
    _name = "account.customers.payment.collection.report"
    _description = "Account Customers Payment Collection Report"

    excel_file = fields.Binary(string="Excel File", readonly=True)
    excel_filename = fields.Char(string="Excel Filename")

    salesperson_id = fields.Many2one(
        comodel_name="res.users",
        string="Salespersons",
        domain=lambda self: self._get_salesperson_domain(),
        help="(365 custom) Select one salesperson to filter the report.",
        required=True,
    )

    date_from = fields.Date(
        string="Date From",
        required=True,
        default=fields.Date.today,
        help="(365 custom) The start date for the report's data range.",
    )
    date_to = fields.Date(
        string="Date To",
        required=True,
        default=fields.Date.today,
        help="(365 custom) The end date for the report's data range.",
    )

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for rec in self:
            if rec.date_from > rec.date_to:
                raise ValidationError(_("วันที่เริ่มต้นต้องไม่มากกว่าวันที่สิ้นสุด"))

    def _get_salesperson_domain(self):
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
            (
                "company_ids",
                "in",
                self.env.company.id,
            ),
        ]

    def _dictfetchall(self):
        cr = self.env.cr
        columns = [col[0] for col in cr.description]
        return [dict(zip(columns, row)) for row in cr.fetchall()]

    def action_excel(self):
        self.ensure_one()

        query = """
            select 
                rp.name              AS partner_name,
                CONCAT_WS(' ', rp.street, rp.street2, rp.city, rcsp.name) AS partner_address,
                rp.ref               AS partner_code,
                am.name              AS invoice_no,
                NULL                 AS not_visit_flag,
                NULL                 AS discount_amount,
                NULL                 AS offset_amount,
                NULL                 AS cash_amount,
                NULL                 AS cheque_amount,
                NULL                 AS transfer_amount,
                NULL                 AS billing_amount,
                NULL                 AS cheque_transfer_date
            from account_move am 
            left join res_partner rp on rp.id = am.partner_id 
            left join res_country_state rcsp ON rp.state_id = rcsp.id
            left join lateral (
                select abl.move_id 
                from account_billing_line abl
                join account_billing ab on ab.id = abl.billing_id 
                where abl.move_id = am.id  
                and ab.state  = 'billed'
                group by abl.move_id 
            ) abl on true
            where 
            am.state = 'posted'
            and abl.move_id is null
            and am.move_type = 'out_invoice'
            and am.payment_state = 'not_paid' 
            AND am.invoice_user_id = %s
            AND am.invoice_date >= %s
            AND am.invoice_date <= %s
            AND am.company_id = %s  -- Prevent Cross Company Data Leak
            ORDER BY rp.name, am.invoice_date, am.name
        """
        params = [
            self.salesperson_id.id,
            self.date_from,
            self.date_to,
            self.env.company.id,
        ]

        self.env.cr.execute(query, params)
        rows = self._dictfetchall()

        excel_content = AccountCustomerPaymentCollectionXlsx().generate_excel(
            rows, self.date_from, self.date_to
        )

        date_from_str = self.date_from.strftime("%d%m%Y")
        date_to_str = self.date_to.strftime("%d%m%Y")

        filename = f"Daily_Sales_Report_{date_from_str}_{date_to_str}.xlsx"

        self.excel_file = base64.b64encode(excel_content)
        self.excel_filename = filename

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/?model={self._name}&id={self.id}&field=excel_file&filename_field=excel_filename&download=true",
            "target": "self",
        }
