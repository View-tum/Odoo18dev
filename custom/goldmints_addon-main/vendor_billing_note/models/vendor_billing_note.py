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
    billing_source = fields.Selection(
        [
            ("empty", "Empty"),
            ("po_service", "PO / Service"),
            ("existing_bills", "Existing APD/CN"),
            ("mixed", "Mixed"),
        ],
        string="Billing Source",
        compute="_compute_billing_summary",
        store=True,
        tracking=True,
    )
    amount_vendor_bills = fields.Monetary(
        string="Vendor Bills",
        compute="_compute_billing_summary",
        currency_field="currency_id",
        store=True,
    )
    amount_residual_net_due = fields.Monetary(
        string="Open Balance",
        compute="_compute_billing_summary",
        currency_field="currency_id",
        store=True,
    )
    
    bill_ids = fields.One2many(
        'account.move', 'vendor_billing_note_id', string='Vendor Bills'
    )
    selected_bill_ids = fields.Many2many(
        "account.move",
        string="Vendor Bills & Credit Notes",
        compute="_compute_selected_bill_ids",
        inverse="_inverse_selected_bill_ids",
        domain="[('move_type', 'in', ('in_invoice', 'in_refund')), ('state', '!=', 'cancel'), ('partner_id', '=', partner_id), ('company_id', '=', company_id)]"
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
    
    @api.depends('purchase_ids.currency_id', 'company_id.currency_id', 'bill_ids.currency_id')
    def _compute_currency_id(self):
        for note in self:
            note.currency_id = note.purchase_ids[:1].currency_id or note.bill_ids[:1].currency_id or note.company_id.currency_id

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

    @api.depends('bill_ids')
    def _compute_selected_bill_ids(self):
        for note in self:
            note.selected_bill_ids = note.bill_ids

    @api.depends(
        "line_ids.price_subtotal",
        "bill_ids",
        "bill_ids.state",
        "bill_ids.move_type",
        "bill_ids.amount_total",
        "bill_ids.amount_residual",
    )
    def _compute_billing_summary(self):
        for note in self:
            valid_bills = note.bill_ids.filtered(lambda move: move.state != "cancel")
            vendor_bills = valid_bills.filtered(lambda move: move.move_type == "in_invoice")
            credit_notes = valid_bills.filtered(lambda move: move.move_type == "in_refund")

            if note.line_ids and valid_bills:
                note.billing_source = "mixed"
            elif valid_bills:
                note.billing_source = "existing_bills"
            elif note.line_ids:
                note.billing_source = "po_service"
            else:
                note.billing_source = "empty"

            currency = note.currency_id or note.company_id.currency_id
            bill_total = sum(abs(move.amount_total) for move in vendor_bills)
            bill_residual = sum(abs(move.amount_residual) for move in vendor_bills)
            credit_residual = sum(abs(move.amount_residual) for move in credit_notes)
            if note.line_ids and note.state == "confirmed":
                bill_residual += sum(note.line_ids.mapped("price_subtotal"))
            note.amount_vendor_bills = currency.round(bill_total)
            note.amount_residual_net_due = currency.round(bill_residual - credit_residual)

    def _validate_selected_bills(self, bills):
        for note in self:
            selected = bills.filtered(lambda move: move.state != "cancel")
            if len(selected) != len(bills):
                raise UserError(_("Cancelled vendor bills or credit notes cannot be selected."))
            invalid_types = selected.filtered(lambda move: move.move_type not in ("in_invoice", "in_refund"))
            if invalid_types:
                raise UserError(_("Only vendor bills and vendor credit notes can be selected."))
            other_notes = selected.filtered(
                lambda move: move.vendor_billing_note_id and move.vendor_billing_note_id != note
            )
            if other_notes:
                raise UserError(
                    _("Some selected APD/CN documents are already linked to another billing note.")
                )
            if selected and any(move.partner_id != note.partner_id for move in selected):
                raise UserError(_("All selected APD/CN documents must belong to the same vendor."))
            if len(selected.mapped("currency_id")) > 1:
                raise UserError(_("All selected APD/CN documents must use the same currency."))
            if len(selected.mapped("company_id")) > 1:
                raise UserError(_("All selected APD/CN documents must belong to the same company."))

    def _inverse_selected_bill_ids(self):
        for note in self:
            current_bills = note.bill_ids
            selected_bills = note.selected_bill_ids
            note._validate_selected_bills(selected_bills)
            for bill in selected_bills - current_bills:
                bill.vendor_billing_note_id = note.id
            for bill in current_bills - selected_bills:
                bill.vendor_billing_note_id = False
            
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

    @api.depends(
        "state",
        "line_ids.price_subtotal",
        "line_ids.tax_ids",
        "bill_ids.amount_total",
        "bill_ids.amount_untaxed",
        "bill_ids.amount_tax",
        "bill_ids.state",
        "bill_ids.move_type",
    )
    def _compute_amount(self):
        for note in self:
            currency = note.currency_id or self.env.company.currency_id
            valid_vendor_bills = note.bill_ids.filtered(lambda b: b.state != 'cancel' and b.move_type == 'in_invoice')
            if note.line_ids:
                amount_untaxed = sum(line.price_subtotal for line in note.line_ids)
                amount_tax = 0.0
                for line in note.line_ids:
                    price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                    taxes = line.tax_ids.compute_all(
                        price,
                        currency,
                        line.quantity,
                        product=line.product_id,
                        partner=note.partner_id,
                    )
                    amount_tax += sum(t.get("amount", 0.0) for t in taxes.get("taxes", []))
                if valid_vendor_bills:
                    if note.state in ("partial_billed", "billed"):
                        amount_untaxed = sum(valid_vendor_bills.mapped("amount_untaxed"))
                        amount_tax = sum(valid_vendor_bills.mapped("amount_tax"))
                    else:
                        amount_untaxed += sum(valid_vendor_bills.mapped("amount_untaxed"))
                        amount_tax += sum(valid_vendor_bills.mapped("amount_tax"))
                note.amount_untaxed = currency.round(amount_untaxed)
                note.amount_tax = currency.round(amount_tax)
                note.amount_total = currency.round(amount_untaxed + amount_tax)
            else:
                amount_untaxed = 0.0
                amount_tax = 0.0
                amount_total = 0.0
                for bill in valid_vendor_bills:
                    amount_untaxed += bill.amount_untaxed
                    amount_tax += bill.amount_tax
                    amount_total += bill.amount_total
                note.amount_untaxed = currency.round(amount_untaxed)
                note.amount_tax = currency.round(amount_tax)
                note.amount_total = currency.round(amount_total)

    def action_confirm(self):
        for record in self:
            if not record.line_ids and not record.bill_ids:
                raise UserError(_("You cannot confirm a billing note without lines or selected bills/credit notes."))
            if record.bill_ids:
                record._validate_selected_bills(record.bill_ids)
            record.state = "confirmed"
            if record.bill_ids:
                record._update_billed_state()

    def action_cancel(self):
        for record in self:
            record.state = "cancel"
            
    def action_create_bill(self):
        self.ensure_one()
        if self.billing_source == "existing_bills":
            raise UserError(
                _("This billing note already uses existing APD/CN documents. You do not need to create another bill.")
            )
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

            existing_move_ids = self.bill_ids.ids
            po.with_context(default_vendor_billing_note_id=self.id).action_create_invoice()
            
            draft_moves = self.env['account.move'].search([
                ('vendor_billing_note_id', '=', self.id),
                ('state', '=', 'draft'),
                ('id', 'not in', existing_move_ids + created_moves.ids)
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
                            # Preserve discount lines (negative subtotal) even if not in billing note
                            if move_line.purchase_line_id.price_subtotal < 0:
                                pass
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
        for note in self:
            if note.state in ('draft', 'cancel'):
                continue
            if not note.line_ids and note.bill_ids:
                note.state = 'billed'
                continue
            total_bn_qty = sum(note.line_ids.mapped('quantity'))
            valid_bills = note.bill_ids.filtered(lambda b: b.state != 'cancel')
            if not valid_bills:
                note.state = 'confirmed'
                continue
            total_billed_qty = 0.0
            for move in valid_bills:
                sign = 1 if move.move_type == 'in_invoice' else -1
                for move_line in move.invoice_line_ids:
                    if move_line.purchase_line_id and move_line.purchase_line_id.id in note.line_ids.mapped('purchase_line_id').ids:
                        total_billed_qty += (move_line.quantity * sign)
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
            for bill in note.bill_ids.filtered(lambda b: b.state != 'cancel' and b.move_type == 'in_refund'):
                refunded += bill.amount_total
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

    def _get_payment_lines(self):
        self.ensure_one()
        valid_account_types = self.env["account.payment"]._get_valid_payment_account_types()
        payable_moves = self.bill_ids.filtered(
            lambda move: move.state == "posted"
            and move.move_type in ("in_invoice", "in_refund")
        )
        return payable_moves.line_ids.filtered(
            lambda line: line.account_type in valid_account_types
            and not line.reconciled
            and not line.company_currency_id.is_zero(line.amount_residual)
        )

    def _get_ap_payment_default_context(self):
        self.ensure_one()
        company = self.company_id or self.env.company
        journal = self.env["account.journal"]
        method_line = self.env["account.payment.method.line"]

        if "pmt_ap_journal_id" in company._fields:
            journal = company.pmt_ap_journal_id
        if "pmt_ap_payment_method_id" in company._fields:
            method_line = company.pmt_ap_payment_method_id

        valid_method = (
            method_line
            and method_line.journal_id == journal
            and method_line.payment_account_id
            and method_line.payment_type == "outbound"
        )
        if not journal or not valid_method:
            method_line = self.env["account.payment.method.line"].search([
                ("payment_type", "=", "outbound"),
                ("payment_account_id", "!=", False),
                ("journal_id.type", "in", ("bank", "cash")),
                ("journal_id.company_id", "=", company.id),
            ], limit=1)
            journal = method_line.journal_id

        context = {}
        if journal:
            context["default_journal_id"] = journal.id
        if method_line:
            context["default_payment_method_line_id"] = method_line.id
        return context

    def _reconcile_bill_credit_residuals(self, payments=None):
        valid_account_types = self.env["account.payment"]._get_valid_payment_account_types()
        payments = payments or self.env["account.payment"]
        payment_lines = payments.move_id.line_ids.filtered(
            lambda line: line.account_type in valid_account_types
            and not line.reconciled
            and not line.company_currency_id.is_zero(line.amount_residual)
        )
        for note in self:
            payable_lines = note.bill_ids.line_ids.filtered(
                lambda line: line.account_type in valid_account_types
                and not line.reconciled
                and not line.company_currency_id.is_zero(line.amount_residual)
            )
            payable_lines |= payment_lines.filtered(lambda line: line.partner_id == note.partner_id)
            grouped_lines = {}
            for line in payable_lines:
                key = (
                    line.company_id.id,
                    line.account_id.id,
                    line.partner_id.id,
                    line.currency_id.id,
                )
                grouped_lines.setdefault(key, self.env["account.move.line"])
                grouped_lines[key] |= line
            for lines in grouped_lines.values():
                currency = lines.company_id[:1].currency_id
                residual = sum(lines.mapped("amount_residual"))
                residual_currency = sum(lines.mapped("amount_residual_currency"))
                same_currency = len(lines.mapped("currency_id")) == 1
                if currency.is_zero(residual) and (not same_currency or lines.currency_id.is_zero(residual_currency)):
                    lines.reconcile()

    def action_register_payment(self):
        self.ensure_one()
        payment_lines = self._get_payment_lines()
        if not payment_lines:
            raise UserError(_("ไม่มีบิลค้างชำระที่สามารถจ่ายเงินได้ในขณะนี้"))
        context = {
            'active_model': 'account.move.line',
            'active_ids': payment_lines.ids,
            'default_group_payment': True,
            'vendor_billing_note_id': self.id,
        }
        if self.bill_ids.filtered(lambda move: move.move_type == "in_refund"):
            context["skip_wht_deduct"] = True
        context.update(self._get_ap_payment_default_context())
        return {
            'name': _('Register Payment'),
            'res_model': 'account.payment.register',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'type': 'ir.actions.act_window',
            'context': context,
        }
