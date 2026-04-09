from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    job_note = fields.Text(related="sale_id.job_request_id.note", readonly=False)
    job_request_count = fields.Integer(compute="_compute_job_request_count")

    def _compute_job_request_count(self):
        for picking in self:
            picking.job_request_count = 1 if picking.sale_id and picking.sale_id.job_request_id else 0

    def action_view_job_request(self):
        self.ensure_one()
        jr = self.sale_id.job_request_id
        if not jr:
            return False
        form_view = self.env.ref("sale_job_request.view_job_request_form").id
        return {
            "type": "ir.actions.act_window",
            "res_model": "job.request",
            "view_mode": "form",
            "views": [(form_view, "form")],
            "res_id": jr.id,
            "target": "current",
        }
