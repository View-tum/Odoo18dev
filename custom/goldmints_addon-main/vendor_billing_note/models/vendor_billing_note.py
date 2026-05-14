from odoo import api, fields, models, _
from odoo.exceptions import UserError


class VendorBillingNote(models.Model):
    _name = "vendor.billing.note"
    _description = "Vendor Billing Note"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(
        string="Billing Note No.",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
        tracking=True,
    )
    vendor_ref = fields.Char(
        string="Vendor Reference",
        tracking=True,
        help="เลขที่ใบวางบิลจาก Supplier",
    )

    partner_id = fields.Many2one(
        "res.partner", 
        string="Vendor", 
        required=True, 
        tracking=True
    )
    service_acceptance_id = fields.Many2one(
        "service.acceptance",
        string="Service Acceptance",
        ondelete="restrict",
        help="Linked Service Acceptance document",
    )
    purchase_ids = fields.Many2many(
        "purchase.order", 
        string="Purchase Orders", 
        compute="_compute_purchase_ids",
        store=True,
        readonly=True
    )
    purchase_count = fields.Integer(
        string="PO Count",
        compute="_compute_purchase_count"
    )

    date = fields.Date(
        string="Billing Date",
        default=fields.Date.context_today,
        required=True,
        tracking=True,
    )
    due_date = fields.Date(
        string="Due Date", 
        tracking=True
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        "res.currency",
        compute="_compute_currency_id",
        store=True,
        string="Currency",
        readonly=True,
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("partial_billed", "Partially Billed"),
            ("billed", "Fully Billed"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        default="draft",
        tracking=True,
    )

    line_ids = fields.One2many(
        "vendor.billing.note.line", 
        "billing_note_id", 
        string="Billing Lines"
    )

    amount_untaxed = fields.Monetary(
        string="Untaxed Amount", 
        store=True, 
        compute="_compute_amount", 
        currency_field="currency_id",
        tracking=True
    )
    amount_tax = fields.Monetary(
        string="Taxes", 
        store=True, 
        compute="_compute_amount",
        currency_field="currency_id"
    )
    amount_total = fields.Monetary(
        string="Total", 
        store=True, 
        compute="_compute_amount", 
        currency_field="currency_id",
        tracking=True
    )
    amount_credit_notes = fields.Monetary(
        string="Credit Notes",
        compute="_compute_credit_amounts",
        currency_field="currency_id",
        store=True,
        tracking=True
    )
    amount_net_due = fields.Monetary(
        string="Amount Due",
        compute="_compute_credit_amounts",
        currency_field="currency_id",
        store=True,
        tracking=True
    )
    
    bill_ids = fields.One2many(
        'account.move', 'vendor_billing_note_id', string='Vendor Bills'
    )
    bill_count = fields.Integer(
        compute='_compute_bill_count', string='Bill Count'
    )
    
    payment_state = fields.Selection(
        [
            ('not_paid', 'Not Paid'),
            ('in_payment', 'In Payment'),
            ('paid', 'Paid'),
            ('partial', 'Partially Paid'),
        ],
        string="Payment Status",
        compute="_compute_payment_state",
        store=True,
        tracking=True
    )
    
    user_id = fields.Many2one(
        'res.users', 
        string='Responsible', 
        default=lambda self: self.env.user,
        tracking=True
    )
    
    note = fields.Html(string="Internal Notes")
    
    @api.depends('line_ids.purchase_order_id')
    def _compute_purchase_ids(self):
        for note in self:
            note.purchase_ids = note.line_ids.mapped('purchase_order_id')
            
    @api.depends('purchase_ids')
    def _compute_purchase_count(self):
        for note in self:
            note.purchase_count = len(note.purchase_ids)
    
    @api.depends('purchase_ids.currency_id', 'company_id.currency_id')
    def _compute_currency_id(self):
        for note in self:
            # ใช้สกุลเงินของ PO ใบแรก (ถ้ามี) ถ้าไม่มีให้ใช้ของบริษัท
            note.currency_id = note.purchase_ids[:1].currency_id or note.company_id.currency_id

    @api.depends('bill_ids.payment_state')
    def _compute_payment_state(self):
        for note in self:
            if not note.bill_ids:
                note.payment_state = 'not_paid'
            else:
                # ดึงสถานะการจ่ายเงินของบิลที่ไม่ได้ถูกยกเลิกมาเช็ค
                valid_bills = note.bill_ids.filtered(lambda b: b.state != 'cancel')
                if not valid_bills:
                    note.payment_state = 'not_paid'
                else:
                    states = valid_bills.mapped('payment_state')
                    if 'partial' in states:
                        note.payment_state = 'partial'
                    elif all(s in ('paid', 'in_payment', 'reversed') for s in states):
                        note.payment_state = 'paid'
                    else:
                        note.payment_state = 'not_paid'
    
    @api.depends('bill_ids')
    def _compute_bill_count(self):
        for note in self:
            note.bill_count = len(note.bill_ids)
            
    def action_view_purchase_order(self):
        self.ensure_one()
        if len(self.purchase_ids) == 1:
            return {
                'name': _('Purchase Order'),
                'type': 'ir.actions.act_window',
                'res_model': 'purchase.order',
                'view_mode': 'form',
                'res_id': self.purchase_ids[0].id,
                'target': 'current',
            }
        return {
            'name': _('Purchase Orders'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.purchase_ids.ids)],
            'target': 'current',
        }
        
    def action_view_vendor_bills(self):
        self.ensure_one()
        # ถ้ามีบิลแค่ 1 ใบ ให้เปิดหน้า Form View ของบิลใบนั้นเลย
        if self.bill_count == 1:
            return {
                'name': _('Vendor Bill'),
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'form',
                'res_id': self.bill_ids[0].id,
                'target': 'current',
            }
        # ถ้ามีบิลหลายใบ (เผื่อกรณีแก้ไข/ยกเลิกแล้วสร้างใหม่) ให้เปิดหน้า List View ก่อน
        return {
            'name': _('Vendor Bills'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.bill_ids.ids)],
            'context': {'default_move_type': 'in_invoice'},
            'target': 'current',
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "vendor.billing.note"
                ) or _("New")
        return super().create(vals_list)

    @api.depends("line_ids.price_subtotal", "line_ids.tax_ids")
    def _compute_amount(self):
        for note in self:
            amount_untaxed = sum(line.price_subtotal for line in note.line_ids)
            amount_tax = 0.0
            
            currency = note.currency_id or self.env.company.currency_id

            for line in note.line_ids:
                taxes = line.tax_ids.compute_all(
                    line.price_unit,
                    currency,
                    line.quantity,
                    product=line.product_id,
                    partner=note.partner_id,
                )
                amount_tax += sum(t.get("amount", 0.0) for t in taxes.get("taxes", []))

            note.amount_untaxed = currency.round(amount_untaxed)
            note.amount_tax = currency.round(amount_tax)
            note.amount_total = currency.round(amount_untaxed + amount_tax)

    def action_confirm(self):
        for record in self:
            if not record.line_ids:
                raise UserError(_("You cannot confirm a billing note without lines."))
            record.state = "confirmed"

    def action_cancel(self):
        for record in self:
            record.state = "cancel"
            
    def action_create_bill(self):
        self.ensure_one()
        if self.state not in ('confirmed', 'partial_billed'):
            raise UserError(_('คุณสามารถสร้างบิลได้เฉพาะใบวางบิลที่ยืนยันแล้ว หรือตั้งหนี้บางส่วนเท่านั้น'))
        
        if not self.purchase_ids:
            return False

        created_moves = self.env['account.move']
        
        # 🌟 รับคำสั่งลับ (Context) ว่าให้สร้างบิลเฉพาะ PO ไหน (ถ้ามี)
        specific_po_id = self.env.context.get('bill_only_po_id')

        po_lines_map = {}
        for line in self.line_ids:
            po = line.purchase_order_id
            if not po:
                continue
            po_lines_map.setdefault(po, self.env['vendor.billing.note.line'])
            po_lines_map[po] |= line

        for po, bn_lines in po_lines_map.items():
            # 🌟 ถ้ามีคำสั่งลับสั่งให้ทำเฉพาะ PO อื่น ให้ข้าม PO นี้ไปเลย!
            if specific_po_id and po.id != specific_po_id:
                continue
                
            # เช็คว่า PO นี้มีของรอตั้งหนี้อยู่ไหม ป้องกันการสร้างบิลเปล่า
            if po.invoice_status != 'to invoice':
                continue

            po.with_context(default_vendor_billing_note_id=self.id).action_create_invoice()
            
            draft_moves = self.env['account.move'].search([
                ('vendor_billing_note_id', '=', self.id),
                ('state', '=', 'draft'),
                ('id', 'not in', created_moves.ids)
            ])
            
            for move in draft_moves:
                lines_to_remove = self.env['account.move.line'] 
                for move_line in move.invoice_line_ids:
                    if move_line.purchase_line_id:
                        matching_bn_line = bn_lines.filtered(
                            lambda l: l.purchase_line_id.id == move_line.purchase_line_id.id
                        )
                        if matching_bn_line:
                            move_line.with_context(check_move_validity=False).quantity = sum(matching_bn_line.mapped('quantity'))
                        else:
                            lines_to_remove |= move_line
                if lines_to_remove:
                    lines_to_remove.with_context(check_move_validity=False).unlink()
            
            created_moves |= draft_moves
            
        # 🌟 สั่งให้ระบบคำนวณสถานะใบวางบิลใหม่ (อัปเดตเป็น Partial หรือ Billed)
        self._update_billed_state()
        
        if not created_moves:
            return True

        if len(created_moves) == 1:
            return {
                'name': _('Vendor Bill'),
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'form',
                'res_id': created_moves.id,
                'target': 'current',
            }
        return {
            'name': _('Vendor Bills'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', created_moves.ids)],
            'target': 'current',
        }
        
    def _update_billed_state(self):
        """คำนวณและอัปเดตสถานะใบวางบิล โดยหักลบจำนวนจาก Credit Note ออกด้วย"""
        for note in self:
            if note.state in ('draft', 'cancel'):
                continue
                
            total_bn_qty = sum(note.line_ids.mapped('quantity'))
            valid_bills = note.bill_ids.filtered(lambda b: b.state != 'cancel')
            
            if not valid_bills:
                note.state = 'confirmed'
                continue
                
            total_billed_qty = 0.0
            for move in valid_bills:
                # 🌟 ถ้ารายการเป็น Credit Note ให้ค่าติดลบ (-1) เพื่อไปหักลดยอดที่ตั้งหนี้ไว้
                sign = 1 if move.move_type == 'in_invoice' else -1
                for move_line in move.invoice_line_ids:
                    if move_line.purchase_line_id and move_line.purchase_line_id.id in note.line_ids.mapped('purchase_line_id').ids:
                        total_billed_qty += (move_line.quantity * sign)
                        
            # เทียบยอดที่ตั้งหนี้สุทธิ (หัก CN แล้ว) กับยอดรวมในใบวางบิล
            if total_billed_qty >= total_bn_qty - 0.001 and total_bn_qty > 0:
                note.state = 'billed'
            elif total_billed_qty > 0.001:
                note.state = 'partial_billed'
            else:
                note.state = 'confirmed'
                
    @api.depends('bill_ids.state', 'bill_ids.amount_total', 'bill_ids.move_type')
    def _compute_credit_amounts(self):
        for note in self:
            refunded = 0.0
            # หาเฉพาะบิลที่เป็น Credit Note (in_refund) ที่เกี่ยวข้องกัน
            for bill in note.bill_ids.filtered(lambda b: b.state != 'cancel' and b.move_type == 'in_refund'):
                refunded += bill.amount_total
            
            # ใช้สกุลเงินในการปัดเศษเพื่อป้องกันปัญหาทศนิยมเกิน
            currency = note.currency_id or self.env.company.currency_id
            note.amount_credit_notes = currency.round(refunded)
            note.amount_net_due = currency.round(note.amount_total - refunded)
    
    def unlink(self):
        for note in self:
            if note.state not in ('draft', 'cancel'):
                raise UserError(
                    _('ไม่อนุญาตให้ลบ! คุณสามารถลบได้เฉพาะใบวางบิลที่มีสถานะ Draft หรือ Cancelled เท่านั้น')
                )
        return super(VendorBillingNote, self).unlink()
