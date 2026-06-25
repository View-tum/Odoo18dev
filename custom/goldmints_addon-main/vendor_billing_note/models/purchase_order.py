from odoo import api, fields, models, _
from odoo.exceptions import UserError

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    billing_note_ids = fields.Many2many(
        "vendor.billing.note", 
        compute="_compute_billing_note_ids", 
        string="Billing Notes"
    )
    billing_note_count = fields.Integer(
        compute="_compute_billing_note_count", string="Billing Note Count"
    )

    is_billing_note_ready = fields.Boolean(
        compute="_compute_is_billing_note_ready", string="Ready for Billing Note"
    )
    
    # --- [เพิ่มฟิลด์ใหม่] เช็คว่าพร้อมสร้างบิลตั้งหนี้หรือยัง ---
    is_ready_to_create_bill = fields.Boolean(
        compute="_compute_is_ready_to_create_bill", string="Ready to Create Bill"
    )
    
    @api.depends("order_line.billing_note_line_ids.billing_note_id")
    def _compute_billing_note_ids(self):
        for order in self:
            # ให้หาเอกสารใบวางบิล โดยอิงจากบรรทัดสินค้า
            order.billing_note_ids = order.order_line.mapped("billing_note_line_ids.billing_note_id")

    @api.depends("billing_note_ids.state", "is_billing_note_ready", "order_line.product_id.type")
    def _compute_is_ready_to_create_bill(self):
        for order in self:
            has_service = any(
                l.product_id.type == 'service'
                for l in order.order_line
                if l.display_type not in ("line_section", "line_note")
            )
            if not has_service:
                order.is_ready_to_create_bill = True
                continue
            confirmed_bns = order.billing_note_ids.filtered(
                lambda b: b.state in ("confirmed", "partial_billed", "billed")
            )
            if not order.is_billing_note_ready and confirmed_bns:
                order.is_ready_to_create_bill = True
            else:
                order.is_ready_to_create_bill = False

    @api.depends("state", "order_line.qty_received", "order_line.product_qty", "order_line.qty_billing_noted", "order_line.product_id.categ_id.is_fixed_asset")
    def _compute_is_billing_note_ready(self):
        for order in self:
            if order.state not in ("purchase", "done"):
                order.is_billing_note_ready = False
                continue

            order.is_billing_note_ready = any(
                l.display_type not in ("line_section", "line_note")
                and l._get_qty_to_billing_note() > 0.001
                for l in order.order_line
            )

    @api.depends("billing_note_ids")
    def _compute_billing_note_count(self):
        for order in self:
            order.billing_note_count = len(order.billing_note_ids)

    def action_create_billing_note(self):
        self.ensure_one()

        lines_to_bill = self.order_line.filtered(
            lambda l: l.display_type not in ("line_section", "line_note")
            and l._get_qty_to_billing_note() > 0.001
        )

        if not lines_to_bill:
            raise UserError(_("ไม่มีรายการที่สามารถวางบิลได้ (สินค้า/บริการถูกวางบิลไปหมดแล้ว)"))

        note_lines = []
        for line in lines_to_bill:
            qty_to_bill = line._get_qty_to_billing_note()
            
            ratio = 1.0
            if line.product_qty:
                ratio = qty_to_bill / line.product_qty
            elif line.qty_received:
                ratio = qty_to_bill / line.qty_received
                
            note_lines.append(
                (
                    0,
                    0,
                    {
                        "purchase_line_id": line.id,
                        "name": line.name,
                        "quantity": qty_to_bill,
                        "price_unit": line.price_unit,
                        "discount": line.discount if hasattr(line, 'discount') else 0.0,
                        "fixed_discount": (line.fixed_discount if hasattr(line, 'fixed_discount') else 0.0) * ratio,
                        "tax_ids": [(6, 0, line.taxes_id.ids)],
                    },
                )
            )

        billing_note = self.env["vendor.billing.note"].create(
            {
                "partner_id": self.partner_id.id,
                "vendor_ref": self.partner_ref or "",
                "line_ids": note_lines,
            }
        )

        return {
            "name": _("Billing Note"),
            "type": "ir.actions.act_window",
            "res_model": "vendor.billing.note",
            "view_mode": "form",
            "res_id": billing_note.id,
            "target": "current",
        }

    def action_view_billing_notes(self):
        self.ensure_one()
        return {
            "name": _("Billing Notes"),
            "type": "ir.actions.act_window",
            "res_model": "vendor.billing.note",
            "view_mode": "list,form",
            "domain": [("id", "in", self.billing_note_ids.ids)], 
            "context": {
                "default_partner_id": self.partner_id.id,
            },
        }

    def action_create_invoice(self):
        if self.env.context.get('default_vendor_billing_note_id'):
            return super(PurchaseOrder, self).action_create_invoice()

        has_service = any(
            any(l.product_id.type == 'service' for l in order.order_line if l.display_type not in ("line_section", "line_note"))
            for order in self
        )
        
        if not has_service:
            return super(PurchaseOrder, self).action_create_invoice()

        for order in self:
            if order.is_billing_note_ready:
                raise UserError(
                    _("ไม่สามารถสร้างบิลได้! กรุณาทำ 'ใบวางบิล' (Billing Note) สำหรับรายการที่เพิ่งรับเข้าให้ครบก่อน")
                )

            confirmed_bns = order.billing_note_ids.filtered(lambda b: b.state in ('confirmed', 'partial_billed'))
            
            lines_to_invoice = order.order_line.filtered(
                lambda l: l.display_type not in ("line_section", "line_note")
                and l.qty_received > l.qty_invoiced
            )

            if lines_to_invoice and not confirmed_bns:
                raise UserError(
                    _("ไม่สามารถสร้างบิลได้! กรุณากดยืนยัน (Confirm) ใบวางบิลก่อนทำการตั้งหนี้")
                )

            multi_po_bns = confirmed_bns.filtered(lambda b: len(b.purchase_ids) > 1)
            
            if multi_po_bns:
                bn = multi_po_bns[0]
                return {
                    'name': 'ตัวเลือกการสร้างบิล (จากใบวางบิลรวม)',
                    'type': 'ir.actions.act_window',
                    'res_model': 'create.bill.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {
                        'default_purchase_id': order.id,
                        'default_billing_note_id': bn.id,
                    }
                }

            for bn in confirmed_bns:
                bn.with_context(bill_only_po_id=order.id).action_create_bill()

        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_in_invoice_type")
        
        invoices = self.invoice_ids.filtered(lambda inv: inv.state == 'draft')
        
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
            action['res_id'] = invoices.id
        else:
            action = {'type': 'ir.actions.act_window_close'}

        return action
    
    def action_create_consolidated_billing_note(self):
        # 1. เช็คก่อนว่า PO ที่เลือกมา เป็นของ Supplier เดียวกันทั้งหมดไหม
        if len(self.mapped('partner_id')) > 1:
            raise UserError(_("คุณไม่สามารถรวบ PO จากซัพพลายเออร์หลายราย ให้อยู่ในใบวางบิลเดียวกันได้!"))
        
        # 2. กรองหาบรรทัดสินค้าที่รับของแล้วแต่ยังไม่ได้วางบิล
        lines_to_bill = self.mapped('order_line').filtered(
            lambda l: l.display_type not in ("line_section", "line_note")
            and l._get_qty_to_billing_note() > 0.001
        )
        
        if not lines_to_bill:
            raise UserError(_("ไม่มีรายการที่สามารถวางบิลได้ จาก PO ที่คุณเลือก! (สินค้าอาจถูกวางบิลไปหมดแล้ว)"))

        # 3. เตรียมข้อมูลบรรทัดใบวางบิล
        note_lines = []
        for line in lines_to_bill:
            qty_to_bill = line._get_qty_to_billing_note()
            
            ratio = 1.0
            if line.product_qty:
                ratio = qty_to_bill / line.product_qty
            elif line.qty_received:
                ratio = qty_to_bill / line.qty_received
                
            note_lines.append((0, 0, {
                "purchase_line_id": line.id,
                "name": line.name,
                "quantity": qty_to_bill,
                "price_unit": line.price_unit,
                "discount": line.discount if hasattr(line, 'discount') else 0.0,
                "fixed_discount": (line.fixed_discount if hasattr(line, 'fixed_discount') else 0.0) * ratio,
                "tax_ids": [(6, 0, line.taxes_id.ids)],
            }))

        # 4. สร้างเอกสารใบวางบิล 1 ใบ
        billing_note = self.env["vendor.billing.note"].create({
            "partner_id": self[0].partner_id.id,
            "line_ids": note_lines,
        })

        # 5. เด้งพา User ไปดูใบวางบิลที่เพิ่งสร้าง
        return {
            "name": _("Billing Note"),
            "type": "ir.actions.act_window",
            "res_model": "vendor.billing.note",
            "view_mode": "form",
            "res_id": billing_note.id,
            "target": "current",
        }

    @api.model
    def action_create_billing_note_from_data(self, partner_id, billing_data):
        """
        สร้างใบวางบิลจากข้อมูลที่ส่งมาจาก Wizard (PO Status Report)
        billing_data: [{'purchase_line_id': ID, 'quantity': QTY, 'picking_id': ID, 'service_acceptance_id': ID}, ...]
        """
        note_lines = []
        for data in billing_data:
            po_line = self.env['purchase.order.line'].browse(data['purchase_line_id'])
            if not po_line.exists():
                continue
            
            ratio = 1.0
            if po_line.product_qty:
                ratio = data['quantity'] / po_line.product_qty
            elif po_line.qty_received:
                ratio = data['quantity'] / po_line.qty_received

            note_lines.append((0, 0, {
                "purchase_line_id": po_line.id,
                "name": po_line.name,
                "quantity": data['quantity'],
                "price_unit": po_line.price_unit,
                "discount": po_line.discount if hasattr(po_line, 'discount') else 0.0,
                "fixed_discount": (po_line.fixed_discount if hasattr(po_line, 'fixed_discount') else 0.0) * ratio,
                "tax_ids": [(6, 0, po_line.taxes_id.ids)],
                "picking_id": data.get('picking_id'),
                "service_acceptance_id": data.get('service_acceptance_id'),
            }))

        if not note_lines:
            raise UserError(_("ไม่พบข้อมูลรายการที่สามารถสร้างใบวางบิลได้"))

        # สร้างใบวางบิล
        billing_note = self.env["vendor.billing.note"].create({
            "partner_id": partner_id,
            "line_ids": note_lines,
        })

        return {
            "name": _("Billing Note"),
            "type": "ir.actions.act_window",
            "res_model": "vendor.billing.note",
            "view_mode": "form",
            "res_id": billing_note.id,
            "target": "current",
        }
