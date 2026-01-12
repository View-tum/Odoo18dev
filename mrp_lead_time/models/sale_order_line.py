from odoo import models, fields, api


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    mfg_lead_time = fields.Integer(
        string="MFG Lead Time (Days)",
        help="(365 custom) Manufacturing lead time for this line item, defaulted from the Product Template.",
    )

    @api.onchange("product_id")
    def _onchange_product_id_process_date(self):
        """
        TH: (Onchange) เมื่อมีการเปลี่ยนสินค้า ระบบจะดึงค่าระยะเวลาการผลิต (MFG Lead Time) จาก Product Template มาใส่ในรายการขายอัตโนมัติ
        EN: (Onchange) When the product is changed, automatically fetches the Manufacturing Lead Time from the Product Template to the sale order line.
        """
        if not self.product_id:
            return

        self.mfg_lead_time = self.product_id.mfg_lead_time
