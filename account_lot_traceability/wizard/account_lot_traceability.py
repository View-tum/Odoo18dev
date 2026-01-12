from odoo import models, fields, api


class AccountLotTraceability(models.TransientModel):
    _name = "account.lot.traceability"
    _description = "Account Lot/Serial Traceability Wizard"

    allowed_product_ids = fields.Many2many(
        comodel_name="product.product",
        compute="_compute_allowed_product_ids",
        string="Allowed Products",
        help="(365 custom) สินค้าที่สามารถเลือกได้ตามหมายเลขล็อตที่เลือก",
    )

    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product",
        domain="[('id', 'in', allowed_product_ids)] if lot_id else []",
        help="(365 custom) เลือกสินค้าเพื่อกรองหมายเลขล็อต (ไม่บังคับ)",
    )

    lot_id = fields.Many2one(
        comodel_name="stock.lot",
        string="Lot/Serial Number",
        required=True,
        domain="[('product_id', '=', product_id)] if product_id else []",
        help="(365 custom) เลือกหมายเลขล็อต/ซีเรียลนัมเบอร์ที่คุณต้องการตรวจสอบย้อนกลับ",
    )

    @api.depends("lot_id")
    def _compute_allowed_product_ids(self):
        """
        TH: คำนวณและตั้งค่ารายการสินค้าที่สามารถเลือกได้ตามหมายเลขล็อตที่เลือก
        EN: Compute and set the list of allowed products based on the selected Lot/Serial Number
        """
        for record in self:
            if record.lot_id:
                same_name_lots = self.env["stock.lot"].search(
                    [("name", "=", record.lot_id.name)]
                )
                record.allowed_product_ids = same_name_lots.mapped("product_id")
                if len(record.allowed_product_ids) == 1:
                    record.product_id = record.allowed_product_ids[0]
            else:
                record.allowed_product_ids = False

    def action_find_invoices(self):
        """
        TH: ค้นหาและแสดงรายการใบแจ้งหนี้ที่เกี่ยวข้องกับ Lot/Serial Number ที่เลือก
            โดยจะตรวจสอบจาก Stock Move ที่สถานะ Done และเป็นขาออก (Outgoing)
        EN: Find and display invoices related to the selected Lot/Serial Number.
            It checks from Stock Moves with 'Done' state and 'Outgoing' picking type.
        """
        self.ensure_one()

        domain = [
            ("lot_id.name", "=", self.lot_id.name),
            ("state", "=", "done"),
            ("picking_id.picking_type_id.code", "=", "outgoing"),
        ]

        if self.product_id:
            domain.append(("product_id", "=", self.product_id.id))

        move_lines = self.env["stock.move.line"].search(domain)

        if not move_lines:
            return {
                "type": "ir.actions.act_window_close",
                "warning": {
                    "title": ("ไม่พบการเคลื่อนไหวของสต็อก"),
                    "message": (
                        "ไม่พบข้อมูลการเคลื่อนไหวของสต็อกสำหรับ Lot/Serial Number ที่เลือก"
                    ),
                },
            }

        result_lines = []
        processed_product_invoice_pairs = set()

        for move_line in move_lines:
            so_line = move_line.move_id.sale_line_id
            if not so_line:
                continue

            invoice_lines = so_line.invoice_lines.filtered(
                lambda x: x.move_id.move_type == "out_invoice"
                and x.move_id.state == "posted"
            )

            for inv_line in invoice_lines:
                invoice = inv_line.move_id
                product = inv_line.product_id

                group_key = (invoice.id, product.id)

                if group_key in processed_product_invoice_pairs:
                    continue
                processed_product_invoice_pairs.add(group_key)
                same_product_lines = invoice.invoice_line_ids.filtered(
                    lambda l: l.product_id == product
                )

                total_amount_product = sum(same_product_lines.mapped("price_subtotal"))
                total_qty_product = sum(same_product_lines.mapped("quantity"))

                avg_price = (
                    total_amount_product / total_qty_product
                    if total_qty_product
                    else 0.0
                )

                vals = {
                    "lot_id": move_line.lot_id.id,
                    "customer_id": invoice.partner_id.id,
                    "invoice_id": invoice.id,
                    "product_id": product.id,
                    "quantity": total_qty_product,
                    "amount_total": total_amount_product,
                    "price_per_unit_calculated": avg_price,
                    "payment_state": invoice.payment_state,
                    "invoice_date": invoice.invoice_date,
                    "sale_order_id": so_line.order_id.id,
                }
                result_lines.append(vals)

        if not result_lines:
            return {
                "type": "ir.actions.act_window_close",
                "warning": {
                    "title": ("ไม่พบใบแจ้งหนี้"),
                    "message": ("ไม่พบใบแจ้งหนี้ที่เกี่ยวข้องกับ Lot/Serial Number ที่เลือก"),
                },
            }

        wizard_lines = self.env["account.lot.traceability.line"].create(result_lines)

        return {
            "name": ("ผลการตรวจสอบการตรวจสอบย้อนกลับของ Lot/Serial: %s")
            % self.lot_id.name,
            "type": "ir.actions.act_window",
            "res_model": "account.lot.traceability.line",
            "view_mode": "list,form",
            "domain": [("id", "in", wizard_lines.ids)],
            "target": "current",
        }
