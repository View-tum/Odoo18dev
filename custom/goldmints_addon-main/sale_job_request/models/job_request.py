from odoo import api, fields, models


class JobRequest(models.Model):
    _name = "job.request"
    _description = "Job Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(required=True, copy=False, default="New", tracking=True)
    sale_id = fields.Many2one("sale.order", tracking=True, copy=False)
    partner_id = fields.Many2one(
        "res.partner",
        string="Customer",
        compute="_compute_partner_id",
        store=True,
        readonly=False,
        tracking=True,
    )
    user_ids = fields.Many2many("res.users", string="Assigned to", default=lambda self: self.env.user)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirm", "Confirm"),
            ("in_progress", "In Progress"),
            ("done", "Done"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        tracking=True,
    )
    note = fields.Text()
    picking_ids = fields.One2many(
        "stock.picking",
        "sale_id",
        string="Delivery Orders",
        compute="_compute_pickings",
        store=False,
    )
    picking_count = fields.Integer(compute="_compute_pickings")
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        compute="_compute_currency_id",
        store=True,
        readonly=False,
    )
    commitment_date = fields.Datetime(
        string="Commitment Date",
        compute="_compute_commitment_date",
        store=True,
        readonly=False,
    )
    order_line_summary = fields.Text(compute="_compute_order_line_summary")
    sale_line_ids = fields.One2many(related="sale_id.order_line", string="Sale Order Lines", readonly=False)
    jr_line_ids = fields.One2many("job.request.line", "job_id", string="Job Request Lines")

    @api.depends("sale_id")
    def _compute_partner_id(self):
        for rec in self:
            if rec.sale_id:
                rec.partner_id = rec.sale_id.partner_id

    @api.depends("sale_id")
    def _compute_currency_id(self):
        for rec in self:
            if rec.sale_id:
                rec.currency_id = rec.sale_id.currency_id
            elif not rec.currency_id:
                rec.currency_id = self.env.company.currency_id

    @api.depends("sale_id")
    def _compute_commitment_date(self):
        for rec in self:
            if rec.sale_id:
                rec.commitment_date = rec.sale_id.commitment_date

    @api.model
    def create(self, vals):
        if not vals.get("name"):
            vals["name"] = "New"
        return super().create(vals)

    @api.depends("sale_id")
    def _compute_pickings(self):
        for rec in self:
            if rec.sale_id:
                pickings = rec.sale_id.picking_ids
                rec.picking_ids = pickings
                rec.picking_count = len(pickings)
            else:
                rec.picking_ids = False
                rec.picking_count = 0

    def action_view_pickings(self):
        self.ensure_one()
        action = self.env.ref("stock.action_picking_tree_all").read()[0]
        action["domain"] = [("id", "in", self.picking_ids.ids)]
        action["context"] = {"default_sale_id": self.sale_id.id}
        return action

    def action_view_sale_order(self):
        self.ensure_one()
        if not self.sale_id:
            return False
        action = self.env.ref("sale.action_orders").read()[0]
        action["res_id"] = self.sale_id.id
        action["view_mode"] = "form"
        return action

    def action_confirm(self):
        seq_date = fields.Date.context_today(self)
        for rec in self:
            if rec.name in (False, "New"):
                rec.name = self.env["ir.sequence"].next_by_code("job.request", sequence_date=seq_date) or rec.name
        self.write({"state": "confirm"})
        for rec in self:
            assignees = rec.user_ids or self.env.user
            names = ", ".join(assignees.mapped("name"))
            rec.message_post(body=f"ยืนยันการรับงาน: งานนี้ได้ถูกส่งให้ผู้รับผิดชอบ ({names}) แล้ว")
            for user in assignees:
                rec.activity_schedule(
                    "mail.mail_activity_data_todo",
                    summary="Job Request Confirmed",
                    note=rec.note or "",
                    user_id=user.id,
                )
        return True

    def action_inprogress(self):
        self.write({"state": "in_progress"})
        for rec in self:
            rec.message_post(body="สถานะงาน: กำลังอยู่ในกระบวนการดำเนินการ")
        return True

    def action_done(self):
        self.write({"state": "done"})
        for rec in self:
            rec.message_post(body="สถานะงาน: ดำเนินการเสร็จสิ้นเรียบร้อยแล้ว")
            rec.activity_unlink(["mail.mail_activity_data_todo"])
        return True

    def action_cancel(self):
        self.write({"state": "cancelled"})
        for rec in self:
            rec.message_post(body="Cancelled")
        return True

    def action_reset_to_draft(self):
        self.write({"state": "draft"})
        for rec in self:
            rec.message_post(body="Reset to Draft")
        return True

    @api.depends("sale_id", "sale_id.order_line", "jr_line_ids", "jr_line_ids.product_id", "jr_line_ids.product_uom_qty")
    def _compute_order_line_summary(self):
        for rec in self:
            lines = []
            if rec.sale_id:
                for l in rec.sale_id.order_line:
                    if l.display_type:
                        continue
                    lines.append(f"{l.product_id.display_name} x {l.product_uom_qty}")
            else:
                for l in rec.jr_line_ids:
                    lines.append(f"{l.product_id.display_name} x {l.product_uom_qty}")
            rec.order_line_summary = "\n".join(lines)
