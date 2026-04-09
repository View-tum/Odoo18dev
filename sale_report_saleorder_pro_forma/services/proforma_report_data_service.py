from odoo import models

class ProformaReportDataService(models.AbstractModel):
    _name = "sale_report_saleorder_pro_forma.proforma_report_data_service"
    _description = "Proforma Report Data Service"

    def prepare(self, orders):
        # TODO: รวม logic formatting, grouping, totals, ฯลฯ
        return {"docs": orders}
