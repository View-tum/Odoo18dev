from odoo import models, fields, api


class AssetHistoryRecord(models.Model):
    _name = "asset.history.record"
    _description = "Asset Modification History"
    _rec_name = "asset_id"

    asset_id = fields.Many2one(
        comodel_name="account.asset",
        string="Asset",
        required=True,
        index=True,
        help="(365 custom) สินทรัพย์ที่ถูกแก้ไข",
    )
    last_modify_action = fields.Selection(
        selection=[
            ("dispose", "Dispose"),
            ("sell", "Sell"),
            ("modify", "Re-evaluate"),
            ("pause", "Pause"),
            ("resume", "Resume"),
        ],
        string="Last Action",
        help="(365 custom) การกระทำล่าสุดที่ทำกับสินทรัพย์",
    )

    invoice_ids = fields.Many2many(
        comodel_name="account.move",
        string="Related Invoices",
        help="(365 custom) ใบแจ้งหนี้ที่เกี่ยวข้องกับการแก้ไขสินทรัพย์",
    )

    last_modified_date = fields.Date(
        string="Last Modified Date",
        default=fields.Date.today,
        help="(365 custom) วันที่แก้ไขล่าสุดของสินทรัพย์",
    )
    note = fields.Text(
        string="Note", help="(365 custom) หมายเหตุเพิ่มเติมเกี่ยวกับการแก้ไขสินทรัพย์"
    )
    _sql_constraints = [
        ("asset_uniq", "unique (asset_id)", "This asset already has a history record!")
    ]
