from datetime import datetime
from odoo import _, api, fields, models


class VendorInherit(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.order"

    # Ensure the wizard's supplier is restricted to vendor partners only
    supplier_id = fields.Many2one(
        'res.partner',
        string='Vendor',
        required=True,
        context={"res_partner_search_mode": "supplier"},
        domain=[('supplier_rank', '>', 0)],
    )

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if "supplier_id" not in fields:
            return res

        active_model = self.env.context.get("active_model", False)
        active_ids = self.env.context.get("active_ids", [])
        target_vendor_id = False
        has_pr_context = False

        if active_ids:
            if active_model == "purchase.request.line":
                lines = self.env["purchase.request.line"].browse(active_ids)
                if lines and lines[0].request_id:
                    has_pr_context = True
                    target_vendor_id = lines[0].request_id.vendor.id if lines[0].request_id.vendor else False

            elif active_model == "purchase.request":
                requests = self.env["purchase.request"].browse(active_ids)
                if requests:
                    has_pr_context = True
                    target_vendor_id = requests[0].vendor.id if requests[0].vendor else False

        if has_pr_context:
            res["supplier_id"] = target_vendor_id

        return res

    # @api.model
    # def default_get(self, fields):
    #     res = super().default_get(fields)
    #     active_model = self.env.context.get("active_model", False)  # ตรวจสอบว่าเป็นโมเดลอะไร
    #     request_line_ids = []
    #     vendor_ids = []  # 🔴 เปลี่ยนตรงนี้ (เดิมเป็น list เปล่า)

    #     if active_model == "purchase.request.line":
    #         request_line_ids += self.env.context.get("active_ids", [])
    #     elif active_model == "purchase.request":
    #         request_ids = self.env.context.get("active_ids", False)  # ดูว่า request ID คืออะไร

    #         # ดึง request line ids จาก purchase request
    #         request_line_ids += self.env[active_model].browse(request_ids).mapped("line_ids.id")
    #         # ดึง vendor จาก purchase request
    #         vendor_ids = self.env[active_model].browse(request_ids).mapped("vendor.id")  # 🔴 เปลี่ยนตรงนี้ (เดิมใช้ +=)

    #     if not request_line_ids:
    #         return res

    #     res["item_ids"] = self.get_items(request_line_ids)
    #     request_lines = self.env["purchase.request.line"].browse(request_line_ids)
    #     supplier_ids = request_lines.mapped("supplier_id").ids

    #     if vendor_ids:
    #         res["supplier_id"] = vendor_ids[0]  # ตั้งค่าจาก vendor ของ purchase request
    #     elif len(supplier_ids) == 1:
    #         res["supplier_id"] = supplier_ids[0]  # ตั้งค่าจาก supplier_id ของ purchase.request.line ถ้ามีค่าเดียว

    #     return res

    # @api.model
    # def _prepare_purchase_order_line(self, po, item):
    #     vals = super()._prepare_purchase_order_line(po, item)  # เรียกใช้งานฟังก์ชันของคลาสแม่
    #
    #     # ปรับค่าที่ต้องการ
    #     # vals["product_uom_qty"] = item.product_qty
    #     vals["product_uom"] = item.product_uom_id.id  # ใช้ product_uom จาก line_id
    #     vals["price_unit"] = item.cost  # แก้ไขค่า price_unit ตาม cost ใหม่
    #
    #     return vals

    def make_purchase_order(self):
        action = super().make_purchase_order()

        purchase_obj = self.env["purchase.order"]
        po_line_obj = self.env["purchase.order.line"]
        pr_line_obj = self.env["purchase.request.line"]
        purchase_ids = action.get("domain", [])[0][2]
        if not purchase_ids:
            return action

        purchases = purchase_obj.browse(purchase_ids)
        for purchase in purchases:
            # --- อัปเดต origin ตาม PR ---
            pr_line_ids = [item.line_id.id for item in self.item_ids if item.line_id]
            pr_lines = pr_line_obj.browse(pr_line_ids)
            origins = [
                pr_line.request_id.name
                for pr_line in pr_lines
                if pr_line.request_id and pr_line.request_id.name
            ]
            if origins:
                purchase.origin = ", ".join(set(origins))

            # --- อัปเดตค่าต่าง ๆ ใน purchase.order.line จาก item ใน wizard ---
            for item in self.item_ids:
                pr_line = item.line_id
                if not pr_line:
                    continue
                po_lines = purchase.order_line.filtered(lambda l: pr_line.id in l.purchase_request_lines.ids)
                for po_line in po_lines:
                    po_line.product_qty = item.product_qty
                    po_line.product_uom = item.product_uom_id
                    po_line.price_unit = item.cost

        return action


class CostAdding(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.order.item"

    cost = fields.Float(
        string="Cost",
        required=False)

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        res.update({
            "keep_description": True,
        })
        return res
