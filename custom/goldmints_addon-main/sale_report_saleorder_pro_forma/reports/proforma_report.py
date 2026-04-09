from odoo import api, models

class ReportSaleProforma(models.AbstractModel):
    _name = "report.sale_report_saleorder_pro_forma.proforma_report_document"
    _description = "Pro-Forma Invoice Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env["sale.order"].browse(docids)
        # ตอนแรกยังไม่ต้องใช้ service ก็ได้ แต่แนะนำให้วางไว้เหมือน stock_count
        return {"docs": docs}
