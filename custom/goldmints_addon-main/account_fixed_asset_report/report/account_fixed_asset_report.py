# -*- coding: utf-8 -*-
import base64
from odoo import models, fields, api
from .account_fixed_asset_report_xlsx import (
    AccountFixedAssetReportXlsx,
    AccountAssetTransactionXlsx,
)


class AccountFixedAssetReport(models.TransientModel):
    _name = "account.fixed.asset.report"
    _description = "Accounting Fixed Asset Report"

    excel_file = fields.Binary(string="Excel File", readonly=True)
    excel_filename = fields.Char(string="Excel Filename")

    asset_model_id = fields.Many2one(
        comodel_name="account.asset",
        domain=[("state", "=", "model")],
        string="หมวดสินทรัพย์",
        help="(365 custom) หมวดสินทรัพย์",
    )
    asset_location_id = fields.Many2one(
        comodel_name="account.analytic.account",
        domain="[('plan_id.is_asset_location', '=', True)]",
        string="สถานที่เก็บสินทรัพย์",
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
        string="สถานะสินทรัพย์",
        help="(365 custom) สถานะสินทรัพย์",
    )
    report_id = fields.Many2one(
        comodel_name="jasper.report",
        string="รายงาน",
        domain=[("model_id", "=", _name)],
        help="(365 custom) เลือกระบุรายงานที่ต้องการ",
    )
    excel_id = fields.Selection(
        selection=[
            ("detailed", "รายงานสินทรัพย์ถาวร"),
            ("summary", "รายงานสรุปการเคลื่อนไหวสินทรัพย์"),
        ],
        string="รายงาน",
        default="detailed",
        help="(365 custom) เลือกรายงานที่ต้องการดาวน์โหลด",
    )

    @api.model
    def default_get(self, fields_list):
        """
        TH: (Override) กำหนดค่าเริ่มต้นสำหรับวันที่ (Date From/To) และเทมเพลตรายงาน
        EN: (Override) Initializes default values for dates (Date From/To) and the report template.
        """
        res = super(AccountFixedAssetReport, self).default_get(fields_list)

        excel_id = res.get("excel_id")

        if "report_id" in fields_list and not res.get("report_id"):
            found_report = self.env["jasper.report"].search(
                [("model_id", "=", self._name)], order="id", limit=1
            )
            if found_report:
                res["report_id"] = found_report.id

        if excel_id:
            config = self.env["account.fixed.asset.config"].search(
                [("excel_id", "=", excel_id)], limit=1
            )
            if config and config.report_id:
                res["report_id"] = config.report_id.id

        return res

    def _dictfetchall(self):
        cr = self.env.cr
        columns = [col[0] for col in cr.description]
        return [dict(zip(columns, row)) for row in cr.fetchall()]

    @api.onchange("excel_id")
    def _onchange_excel_id(self):
        """
        เมื่อมีการเลือกประเภทรายงาน Excel ให้ไปค้นหาค่า report_id (Jasper)
        ที่ตั้งค่าไว้ใน Config มาใส่ให้โดยอัตโนมัติ
        """
        if self.excel_id:
            config = self.env["account.fixed.asset.config"].search(
                [("excel_id", "=", self.excel_id)], limit=1
            )

            if config and config.report_id:
                self.report_id = config.report_id.id
            else:
                self.report_id = False

    def excel_transaction_summary(self):
        self.ensure_one()
        # ค้นหา Assets ตามเงื่อนไขในหน้าจอ
        domain = []
        if self.asset_model_id:
            domain.append(("model_id", "=", self.asset_model_id.id))
        if self.asset_location_id:
            domain.append(("asset_location_id", "=", self.asset_location_id.id))
        if self.asset_status:
            domain.append(("state", "=", self.asset_status))

        assets = self.env["account.asset"].search(domain)
        asset_data_list = []

        for asset in assets:
            moves = self.env["account.move"].search(
                [
                    ("asset_id", "in", [asset.id]),
                    ("state", "=", "posted"),
                ]
            )

            moves = moves.sorted(key=lambda m: m.date or fields.Date.today())
            transactions = []
            for move in moves:
                transactions.append(
                    {
                        "date": move.date if move.date else "",
                        "voucher": move.name if move.name else "",
                        "description": (
                            move.asset_move_type
                            + " since "
                            + move.asset_depreciation_beginning_date.strftime(
                                "%d-%m-%Y"
                            )
                            if move.asset_depreciation_beginning_date
                            else move.asset_move_type
                        ),
                        "type": move.asset_move_type if move.asset_move_type else "",
                        "amount": (
                            -(move.depreciation_value) if move.depreciation_value else 0
                        ),
                        "amount_curr": (
                            -(move.depreciation_value) if move.depreciation_value else 0
                        ),
                        "currency": move.currency_id.name if move.currency_id else "",
                    }
                )

            asset_data_list.append(
                {
                    "group": asset.model_id.name if asset.model_id else "",
                    "number": (
                        asset.asset_register_number
                        if asset.asset_register_number
                        else ""
                    ),
                    "name": asset.name if asset.name else "",
                    "book": asset.journal_id.name if asset.journal_id else "",
                    "book_type": asset.journal_id.type if asset.journal_id else "",
                    "status": dict(self._fields["asset_status"].selection).get(
                        asset.state
                    ),
                    "location": (
                        asset.asset_location_id.name if asset.asset_location_id else ""
                    ),
                    "acquisition": asset.original_value if asset.original_value else 0,
                    "acquisition_date": (
                        asset.acquisition_date if asset.acquisition_date else ""
                    ),
                    "currency": asset.currency_id.name if asset.currency_id else "",
                    "net_book_value": asset.book_value if asset.book_value else 0,
                    "transactions": transactions,
                }
            )

        # เรียกใช้ Class ใหม่สร้างไฟล์
        excel_content = AccountAssetTransactionXlsx().generate_excel(asset_data_list)

        self.excel_file = base64.b64encode(excel_content)
        self.excel_filename = f"รายงานการเคลื่อนไหวสินทรัพย์_{fields.Date.today()}.xlsx"

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/?model={self._name}&id={self.id}&field=excel_file&filename_field=excel_filename&download=true",
            "target": "self",
        }

    def excel_fixed_asset(self):
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

        filename = (
            f"รายงานสินทรัพย์ถาวร_{fields.Date.today().strftime('%d-%m-%Y')}.xlsx"
        )

        self.excel_file = base64.b64encode(excel_content)
        self.excel_filename = filename

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/?model={self._name}&id={self.id}&field=excel_file&filename_field=excel_filename&download=true",
            "target": "self",
        }

    def action_excel_report(self):
        if self.excel_id == "summary":
            return self.excel_transaction_summary()
        elif self.excel_id == "detailed":
            return self.excel_fixed_asset()
        else:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "การตั้งค่าไม่ถูกต้อง",
                    "message": "  • ไม่พบประเภทไฟล์ Excel กรุณาตรวจสอบการตั้งค่า",
                    "type": "warning",
                    "sticky": False,
                },
            }

    def action_print_report(self):
        self.ensure_one()

        if not self.report_id:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "การตั้งค่าไม่ถูกต้อง",
                    "message": "  • ไม่พบประเภทไฟล์ PDF กรุณาตรวจสอบการตั้งค่า",
                    "type": "warning",
                    "sticky": False,
                },
            }

        data = {
            "asset_status": self.asset_status if self.asset_status else None,
            "asset_model_ids": (
                ",".join(map(str, self.asset_model_id.ids))
                if self.asset_model_id
                else None
            ),
            "asset_location_ids": (
                ",".join(map(str, self.asset_location_id.ids))
                if self.asset_location_id
                else None
            ),
        }

        return self.report_id.run_report(docids=[self.ids[0]], data=data)
