# -*- coding: utf-8 -*-
import base64
from odoo import models, fields, api
from .account_fixed_asset_report_xlsx import (
    AccountFixedAssetReportXlsx,
)


class AccountFixedAssetReport(models.TransientModel):
    _name = "account.fixed.asset.report"
    _description = "Accounting Fixed Asset Report"

    excel_file = fields.Binary(string="Excel File", readonly=True)
    excel_filename = fields.Char(string="Excel Filename")

    asset_model_id = fields.Many2one(
        comodel_name="account.asset",
        domain=[("state", "=", "model")],
        string="Asset Group",
        help="(365 custom) หมวดสินทรัพย์",
    )

    asset_location_id = fields.Many2one(
        comodel_name="account.analytic.account",
        domain="[('plan_id.is_asset_location', '=', True)]",
        string="Asset Location",
        help="(365 custom) แผนกงาน/สถานที่เก็บสินทรัพย์",
    )

    asset_status = fields.Selection(
        selection=[
            ("model", "Model"),
            ("draft", "Draft"),
            ("open", "Running"),
            ("paused", "On Hold"),
            ("close", "Closed"),
            ("cancelled", "Cancelled"),
            ("dispose", "Dispose"),
            ("sell", "Sell"),
            ("modify", "Re-evaluate"),
            ("pause", "Pause"),
            ("resume", "Resume"),
        ],
        string="Asset Status",
        help="(365 custom) สถานะสินทรัพย์",
    )

    def _dictfetchall(self):
        cr = self.env.cr
        columns = [col[0] for col in cr.description]
        return [dict(zip(columns, row)) for row in cr.fetchall()]

    def action_excel(self):
        self.ensure_one()

        where_clauses = []
        params = []
        join_clauses = ["left join account_asset aa2 on aa2.id = aa.model_id"]
        is_modify_join = False

        # --- Asset Model ---
        if self.asset_model_id:
            where_clauses.append("aa.model_id = %s")
            params.append(self.asset_model_id.id)

        # --- Asset Location ---
        if self.asset_location_id:
            where_clauses.append("aa.asset_location_id = %s")
            params.append(self.asset_location_id.id)

        # --- Asset Status (จุดที่ทำ Dynamic) ---
        if self.asset_status:
            modify_actions = ["dispose", "sell", "modify", "pause", "resume"]
            if self.asset_status in modify_actions:
                is_modify_join = True
                join_clauses.append(
                    "left join asset_history_record ahr on ahr.asset_id = aa.id"
                )
                where_clauses.append("ahr.last_modify_action = %s")
            else:
                where_clauses.append("aa.state = %s")

            params.append(self.asset_status)

        select_status = (
            "COALESCE(ahr.last_modify_action, aa.state)"
            if is_modify_join
            else """
            COALESCE(
                (SELECT last_modify_action FROM asset_history_record WHERE asset_id = aa.id), 
                aa.state
            )
        """
        )

        query = f"""
            SELECT DISTINCT
                aa.original_value,
                aa.name AS asset_name,
                aa2.name AS asset_model,
                aa.acquisition_date,
                aa.disposal_date,
                aa.method_number AS duration,
                aa.book_value,
                {select_status} AS detailed_status,
                (
                    SELECT STRING_AGG(move.name, ', ')
                    FROM account_move move
                    JOIN account_move_asset_history_record_rel rel ON rel.account_move_id = move.id
                    JOIN asset_history_record ahr_sub ON ahr_sub.id = rel.asset_history_record_id
                    
                    WHERE ahr_sub.asset_id = aa.id
                    AND move.move_type = 'out_invoice' 
                    AND move.state = 'posted'
                ) AS invoice_name
                
            FROM
                account_asset aa
            {' '.join(join_clauses)}
        """

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)

        self.env.cr.execute(query, params)
        rows = self._dictfetchall()

        excel_content = AccountFixedAssetReportXlsx().generate_excel(rows)

        filename = f"Fixed_Asset_Report.xlsx"

        self.excel_file = base64.b64encode(excel_content)
        self.excel_filename = filename

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/?model={self._name}&id={self.id}&field=excel_file&filename_field=excel_filename&download=true",
            "target": "self",
        }
