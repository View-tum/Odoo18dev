from odoo import models, fields, api


class AssetModify(models.TransientModel):
    _inherit = "asset.modify"

    def _create_or_update_history(self):
        """
        TH: สร้างหรืออัปเดตบันทึกประวัติการแก้ไขสินทรัพย์
        EN: Create or update asset modification history record
        """
        HistoryModel = self.env["asset.history.record"]

        for wizard in self:
            existing_record = HistoryModel.search(
                [("asset_id", "=", wizard.asset_id.id)], limit=1
            )

            vals = {
                "last_modify_action": wizard.modify_action,
                "last_modified_date": wizard.date,
                "note": wizard.name,
            }

            if wizard.modify_action == "sell":
                vals["invoice_ids"] = [
                    (4, invoice_id) for invoice_id in wizard.invoice_ids.ids
                ]

            if existing_record:
                existing_record.write(vals)
            else:
                vals["asset_id"] = wizard.asset_id.id
                HistoryModel.create(vals)

    def sell_dispose(self):
        """
        TH: ดำเนินการขายหรือจำหน่ายสินทรัพย์และบันทึกประวัติการแก้ไข
        EN: Process asset sell or dispose and record modification history
        """
        res = super(AssetModify, self).sell_dispose()
        self._create_or_update_history()
        return res

    def modify(self):
        """
        TH: ดำเนินการปรับปรุงมูลค่าสินทรัพย์และบันทึกประวัติการแก้ไข
        EN: Process asset re-evaluation and record modification history
        """
        res = super(AssetModify, self).modify()
        self._create_or_update_history()
        return res

    def pause(self):
        """
        TH: ดำเนินการระงับสินทรัพย์และบันทึกประวัติการแก้ไข
        EN: Process asset pause and record modification history
        """
        res = super(AssetModify, self).pause()
        self._create_or_update_history()
        return res
