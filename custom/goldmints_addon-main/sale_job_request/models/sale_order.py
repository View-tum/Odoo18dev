from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    job_request_id = fields.Many2one("job.request", copy=False)
    job_note = fields.Text(related="job_request_id.note", readonly=False)
    job_request_count = fields.Integer(compute="_compute_job_request_count")

    def _compute_job_request_count(self):
        for order in self:
            order.job_request_count = 1 if order.job_request_id else 0

    def action_create_job_request(self):
        for order in self:
            if order.job_request_id:
                continue
            jr_vals = {
                "sale_id": order.id,
                "note": order.job_note,
                "user_ids": [(4, self.env.user.id)],
            }
            jr = self.env["job.request"].create(jr_vals)
            order.job_request_id = jr
        return self.action_view_job_request()

    def action_view_job_request(self):
        self.ensure_one()
        if not self.job_request_id:
            return self.action_create_job_request()
        form_view = self.env.ref("sale_job_request.view_job_request_form").id
        return {
            "type": "ir.actions.act_window",
            "res_model": "job.request",
            "view_mode": "form",
            "views": [(form_view, "form")],
            "res_id": self.job_request_id.id,
            "target": "current",
        }
