from odoo import models, api, _

class ReportMBR(models.AbstractModel):
    _name = "report.mbr_financial_report.mbr_report_template"
    _description = "MBR Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env["mbr.report.wizard"].browse(docids)
        mbr_data = docs.compute_mbr()
        return {
            "doc_ids": docids,
            "doc_model": "mbr.report.wizard",
            "docs": docs,
            "mbr": mbr_data,
        }


