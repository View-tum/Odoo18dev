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

    @api.depends("billing_note_ids.state", "is_billing_note_ready")
    def _compute_is_ready_to_create_bill(self):
        for order in self:
            confirmed_bns = order.billing_note_ids.filtered(
                lambda b: b.state in ("confirmed", "partial_billed", "billed")
            )
            # ปุ่ม Create Bill จะแสดงก็ต่อเมื่อ:
            # 1. ไม่มีของค้างวางบิลแล้ว (is_billing_note_ready == False) 
            # 2. มีใบวางบิลที่ Confirm แล้วอย่างน้อย 1 ใบ
            if not order.is_billing_note_ready and confirmed_bns:
                order.is_ready_to_create_bill = True
            else:
                order.is_ready_to_create_bill = False

    @api.depends("state", "order_line.qty_received", "order_line.qty_billing_noted")
    def _compute_is_billing_note_ready(self):
        for order in self:
            if order.state not in ("purchase", "done"):
                order.is_billing_note_ready = False
                continue

            order.is_billing_note_ready = any(
                l.display_type not in ("line_section", "line_note")
                and (l.qty_received - l.qty_billing_noted) > 0.001
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
            and (l.qty_received - l.qty_billing_noted) > 0.001
        )

        if not lines_to_bill:
            raise UserError(_("ไม่มีรายการที่สามารถวางบิลได้ (สินค้า/บริการถูกวางบิลไปหมดแล้ว)"))

        note_lines = []
        for line in lines_to_bill:
            qty_to_bill = line.qty_received - line.qty_billing_noted
            note_lines.append(
                (
                    0,
                    0,
                    {
                        "purchase_line_id": line.id,
                        "name": line.name,
                        "quantity": qty_to_bill,
                        "price_unit": line.price_unit,
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
        """บังคับ Flow และจัดการการสร้างบิลจากหน้า PO โดยเชื่อมกับใบวางบิล"""
        
        # 1. หากกดมาจากหน้า "ใบวางบิล" (มี Context ส่งมา) ให้ทะลุไปสร้างบิลตามมาตรฐาน Odoo เลย
        if self.env.context.get('default_vendor_billing_note_id'):
            return super(PurchaseOrder, self).action_create_invoice()

        # 2. กรณีผู้ใช้กดปุ่ม "Create Bill" จากหน้าจอ PO เอง
        for order in self:
            # เช็คว่ายังมีของค้างไม่ได้ทำใบวางบิลไหม
            if order.is_billing_note_ready:
                raise UserError(
                    _("ไม่สามารถสร้างบิลได้! กรุณาทำ 'ใบวางบิล' (Billing Note) สำหรับรายการที่เพิ่งรับเข้าให้ครบก่อน")
                )

            # 🌟 [แก้จุดที่ 1] กรองหาเฉพาะใบวางบิลที่ "ยืนยันแล้ว" หรือ "ตั้งหนี้บางส่วนแล้ว"
            confirmed_bns = order.billing_note_ids.filtered(lambda b: b.state in ('confirmed', 'partial_billed'))
            
            # เช็ครายการที่ยังไม่ได้ตั้งหนี้
            lines_to_invoice = order.order_line.filtered(
                lambda l: l.display_type not in ("line_section", "line_note")
                and l.qty_received > l.qty_invoiced
            )

            # ถ้ามีของต้องเปิดบิล แต่ไม่มี BN ที่ confirmed เลย
            if lines_to_invoice and not confirmed_bns:
                raise UserError(
                    _("ไม่สามารถสร้างบิลได้! กรุณากดยืนยัน (Confirm) ใบวางบิลก่อนทำการตั้งหนี้")
                )

            # 🌟 [แก้จุดที่ 2] ตรวจสอบว่ามีใบวางบิลที่มัดรวม PO หลายใบหรือไม่ (เพื่อเด้ง Wizard)
            multi_po_bns = confirmed_bns.filtered(lambda b: len(b.purchase_ids) > 1)
            
            if multi_po_bns:
                # ดึงใบแรกที่เจอมาแสดงใน Wizard
                bn = multi_po_bns[0]
                return {
                    'name': 'ตัวเลือกการสร้างบิล (จากใบวางบิลรวม)',
                    'type': 'ir.actions.act_window',
                    'res_model': 'create.bill.wizard',
                    'view_mode': 'form',
                    'target': 'new', # เปิดเป็น Pop-up
                    'context': {
                        'default_purchase_id': order.id,
                        'default_billing_note_id': bn.id,
                    }
                }

            # 3. ถ้าใบวางบิลเป็นแบบ 1 PO ปกติ ก็วนลูปสร้าง Vendor Bill แยกทีละใบ
            for bn in confirmed_bns:
                # สั่งให้ใบวางบิลรันฟังก์ชันสร้างบิลของตัวเอง (ซึ่งจะตัดยอด Partial และผูก Ref ให้เรียบร้อย)
                # แถม Context ไปให้มันรู้ว่าให้สร้างเฉพาะของ PO นี้นะ (เผื่อมีกรณีหลุดรอด)
                bn.with_context(bill_only_po_id=order.id).action_create_bill()

        # 4. หลังจากระบบสร้างบิลเบื้องหลังเสร็จหมดแล้ว ให้เปิดหน้าต่างพาผู้ใช้ไปดู Vendor Bill
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_in_invoice_type")
        
        # ค้นหา Vendor Bill ทั้งหมดของ PO ใบนี้ที่เพิ่งถูกสร้าง (Draft)
        invoices = self.invoice_ids.filtered(lambda inv: inv.state == 'draft')
        
        if len(invoices) > 1:
            # ถ้าสร้างออกมาหลายใบ (เช่น มี 2 Confirmed BN) ให้แสดงเป็นหน้าจอ List (ตาราง)
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            # ถ้ามีใบเดียว ให้เปิดหน้าจอ Form ของบิลใบนั้นเลย
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
            and (l.qty_received - l.qty_billing_noted) > 0.001
        )
        
        if not lines_to_bill:
            raise UserError(_("ไม่มีรายการที่สามารถวางบิลได้ จาก PO ที่คุณเลือก! (สินค้าอาจถูกวางบิลไปหมดแล้ว)"))

        # 3. เตรียมข้อมูลบรรทัดใบวางบิล
        note_lines = []
        for line in lines_to_bill:
            qty_to_bill = line.qty_received - line.qty_billing_noted
            note_lines.append((0, 0, {
                "purchase_line_id": line.id,
                "name": line.name,
                "quantity": qty_to_bill,
                "price_unit": line.price_unit,
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
            
            note_lines.append((0, 0, {
                "purchase_line_id": po_line.id,
                "name": po_line.name,
                "quantity": data['quantity'],
                "price_unit": po_line.price_unit,
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