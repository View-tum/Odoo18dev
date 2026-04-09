from odoo import models, fields, api

_SERVICE_STATUS = [
    ('not_validated', 'ยังไม่ตรวจสอบ'),
    ('validated', 'ตรวจสอบแล้ว'),
]


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    has_service_lines = fields.Boolean(
        string='มีบริการในรายการ',
        compute='_compute_service_status',
        store=True,
        readonly=True)

    service_status = fields.Selection(
        _SERVICE_STATUS,
        string='สถานะบริการ',
        default='not_validated',
        store=True,
        readonly=True,
        copy=False)

    service_line_count = fields.Integer(
        string='จำนวนบริการ',
        compute='_compute_service_status',
        store=True,
        readonly=True)

    service_validated = fields.Boolean(
        string='ตรวจสอบบริการแล้ว',
        default=False,
        store=True,
        readonly=True,
        copy=False)

    @api.depends('order_line.product_id', 'order_line.product_id.type')
    def _compute_service_status(self):
        for order in self:
            service_lines = [
                l for l in order.order_line if l.product_id and l.product_id.type == 'service']
            order.has_service_lines = bool(service_lines)
            order.service_line_count = len(service_lines)

    def button_validate(self):
        self.ensure_one()
        if self.has_service_lines:
            self.write({'service_status': 'validated',
                       'service_validated': True})
        return True

    def action_view_service_lines(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"].sudo()._for_xml_id(
            "purchase.purchase_order_line_action")
        action['domain'] = [('order_id', '=', self.id),
                            ('product_id.type', '=', 'service')]
        return action


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    service_qty_received = fields.Float(
        string='บริการได้รับแล้ว',
        default=0.0,
        copy=False,
        help='จำนวนบริการที่ได้รับจริง ใช้สำหรับตรวจสอบความครบถ้วนของบริการ')
