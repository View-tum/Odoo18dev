# -*- coding: utf-8 -*-
from odoo import api, models, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = 'purchase.request.line.make.purchase.order'

    @api.model
    def default_get(self, fields):
      
        res = super().default_get(fields)
        active_model = self.env.context.get('active_model')
        active_ids = self.env.context.get('active_ids') or []

        if active_model == 'purchase.request.line' and active_ids:
            lines = self.env['purchase.request.line'].browse(active_ids)

            # 1) ต้องมี Supplier ครบทุกบรรทัด
            partners = lines.mapped('supplier_id')
            if not partners or any(not p for p in partners):
                raise ValidationError(_(
                    "พบรายการใบขอซื้อ (Purchase Request Line) ที่ยังไม่ได้ระบุผู้ขาย (Supplier)\n"
                    "กรุณาระบุผู้ขายให้ครบทุกบรรทัดก่อนดำเนินการสร้างใบเสนอราคา (RFQ)"
                ))

            # 2) ต้องเป็น Supplier เดียวกันทั้งหมด
            supplier_ids = set(p.id for p in partners if p)
            _logger.debug("PR Create RFQ suppliers=%s, lines=%s", supplier_ids, active_ids)

            if len(supplier_ids) > 1:
                req_names = ', '.join(sorted(set(lines.mapped('request_id.name'))))
                raise ValidationError(_(
                    "ไม่สามารถสร้างใบเสนอราคา (RFQ) เดียวจากหลายผู้ขายได้\n"
                    "กรุณาเลือกบรรทัดใบขอซื้อ (PR Lines) ที่มีผู้ขายคนเดียวกันเท่านั้น\n\n"
                    "รายการใบขอซื้อที่เลือก: %s"
                ) % req_names)

        return res

    def make_purchase_order(self):
        """
        ดักอีกชั้นตอนกดยืนยัน (Confirm) ภายใน Wizard
        """
        self.ensure_one()
        active_model = self.env.context.get('active_model')
        active_ids = self.env.context.get('active_ids') or []

        if active_model == 'purchase.request.line' and active_ids:
            lines = self.env['purchase.request.line'].browse(active_ids)

            partners = lines.mapped('supplier_id')
            if not partners or any(not p for p in partners):
                raise ValidationError(_(
                    "พบรายการใบขอซื้อ (Purchase Request Line) ที่ยังไม่ได้ระบุผู้ขาย (Supplier)\n"
                    "กรุณาระบุผู้ขายให้ครบทุกบรรทัดก่อนดำเนินการสร้างใบเสนอราคา (RFQ)"
                ))

            supplier_ids = set(p.id for p in partners if p)
            if len(supplier_ids) > 1:
                raise ValidationError(_(
                    "ไม่สามารถสร้างใบเสนอราคา (RFQ) เดียวจากหลายผู้ขายได้\n"
                    "กรุณาเลือกบรรทัดใบขอซื้อ (PR Lines) ที่มีผู้ขายคนเดียวกันเท่านั้น"
                ))

        return super().make_purchase_order()
