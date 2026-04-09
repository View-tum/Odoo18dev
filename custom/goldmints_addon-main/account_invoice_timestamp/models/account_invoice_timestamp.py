# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AccountInvoiceTimestamp(models.Model):
    _name = "account.invoice.timestamp"
    _description = "Account Invoice Timestamp Log"
    _order = "timestamp desc"

    name = fields.Char(
        compute="_compute_name",
        store=True,
        string="Name",
        help="(365 custom) Record Name (Auto-generated from: User - Timestamp).",
    )
    timestamp = fields.Datetime(
        string="Timestamp",
        default=fields.Datetime.now,
        readonly=True,
        required=True,
        index=True,
        help="(365 custom) Date and time of recording (System generated).",
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Confirmed By",
        default=lambda self: self.env.user,
        readonly=True,
        required=True,
        help="(365 custom) User who confirmed or recorded this entry.",
    )
    invoice_ids = fields.Many2many(
        comodel_name="account.move",
        string="Invoices",
        readonly=True,
        help="(365 custom) List of all Invoices specified in this Log set.",
    )

    @api.depends("timestamp", "user_id")
    def _compute_name(self):
        """
        TH: (Compute) คำนวณและกำหนดชื่อรายการ Log โดยนำชื่อผู้ใช้มารวมกับเวลาที่บันทึก (แปลงเป็นเวลาท้องถิ่น) ในรูปแบบ "User - DD-MM-YYYY HH:MM:SS"
        EN: (Compute) Computes and sets the log record name by combining the user's name with the recorded timestamp (converted to local time) in the format "User - DD-MM-YYYY HH:MM:SS".
        """
        for record in self:
            if record.timestamp and record.user_id:
                local_timestamp = fields.Datetime.context_timestamp(
                    record, record.timestamp
                )
                formatted_timestamp = local_timestamp.strftime("%d-%m-%Y %H:%M:%S")
                record.name = f"{record.user_id.name} - {formatted_timestamp}"
            else:
                record.name = "Anonymous"
