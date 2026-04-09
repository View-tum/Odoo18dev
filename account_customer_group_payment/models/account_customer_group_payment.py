# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AccountCustomerGroupPayment(models.Model):

    _name = "account.customer.group.payment"
    _description = "รับชำระเงินกลุ่มบริษัท (แม่–ลูก)"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string="Name", compute="_compute_name", store=True)

    @api.depends("parent_partner_id")
    def _compute_name(self):
        for record in self:
            if record.parent_partner_id:
                record.name = _("Group Payment: %s") % record.parent_partner_id.name
            else:
                record.name = _("Group Payment")

    # 6 ช่องหลัก
    parent_partner_id = fields.Many2one(
        "res.partner",
        string="บริษัทแม่",
        required=True,
        domain="[('is_company', '=', True), ('customer_rank', '>', 0), '|', ('parent_id', '!=', False), ('child_ids', '!=', False)]",
        help="เลือกบริษัทแม่ หรือบริษัทลูกที่มีความสัมพันธ์ parent/child (Contact ฝั่งลูกค้า)",
        tracking=True,
    )
    group_root_partner_id = fields.Many2one(
        "res.partner",
        string="รากกลุ่มบริษัท",
        compute="_compute_group_root_partner",
        store=True,
        readonly=True,
    )
    child_partner_ids = fields.Many2many(
        "res.partner",
        string="บริษัทลูก",
        domain="[('customer_rank', '>', 0), ('id', 'child_of', group_root_partner_id), ('id', '!=', group_root_partner_id)]",
        help="เลือกลูกค้าในกลุ่มเดียวกัน (สาขา/บริษัทลูกภายใต้ root เดียวกัน)",
    )
    payer_partner_id = fields.Many2one(
        "res.partner",
        string="ใครเป็นผู้จ่าย",
        required=True,
        domain="[('is_company', '=', True), ('customer_rank', '>', 0), ('id', 'child_of', group_root_partner_id)]",
        help="เลือกบริษัทแม่หรือลูกที่เป็นผู้โอนเงินจริง (ต้องอยู่ในกลุ่มเดียวกัน)",
        tracking=True,
    )
    payment_journal_id = fields.Many2one(
        "account.journal",
        string="บัญชีธนาคารที่ใช้รับเงิน",
        domain="[('type', 'in', ('bank', 'cash')), ('company_id', '=', company_id)]",
        required=True,
        help="สมุดเงินสด/ธนาคารของบริษัทเรา ใช้รับเงินจากลูกค้ากลุ่มนี้",
        tracking=True,
    )
    payment_date = fields.Date(
        string="วันที่จ่าย",
        default=fields.Date.context_today,
        required=True,
        tracking=True,
    )
    filter_date_from = fields.Date(
        string="วันที่ใบแจ้งหนี้ ตั้งแต่",
        help="ใช้กรองวันที่ใบแจ้งหนี้ (invoice_date) เริ่มต้น หากเว้นว่างจะไม่กรอง",
    )
    filter_date_to = fields.Date(
        string="ถึงวันที่",
        help="ใช้กรองวันที่ใบแจ้งหนี้ (invoice_date) สิ้นสุด หากเว้นว่างจะไม่กรอง",
    )
    filter_min_amount = fields.Monetary(
        string="ยอดค้างขั้นต่ำ",
        currency_field="currency_id",
        help="กรองยอดคงค้างตั้งแต่จำนวนนี้ขึ้นไป",
    )
    total_selected_amount = fields.Monetary(
        string="ยอดรวมที่เลือก",
        compute="_compute_total_selected_amount",
        currency_field="currency_id",
        readonly=True,
        store=True,
        tracking=True,
    )

    memo = fields.Char(
        string="Memo",
        compute="_compute_memo",
        store=True,
        readonly=False,
        tracking=True,
        help="Memo for this group payment record",
    )

    @api.depends('payer_partner_id')
    def _compute_memo(self):
        for record in self:
            if record.payer_partner_id:
                record.memo = _("Group payment by %s") % record.payer_partner_id.display_name
            else:
                record.memo = ""

    # บริษัท/สกุลเงินอ้างอิง
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="สกุลเงิน",
        related="company_id.currency_id",
        readonly=True,
    )

    # รายการเอกสาร
    line_ids = fields.One2many(
        "account.customer.group.payment.line",
        "payment_id",
        string="เอกสารที่เลือก",
    )
    summary_info = fields.Char(
        string="สรุปการรับชำระ",
        compute="_compute_summary_info",
        readonly=True,
    )
    state = fields.Selection(
        [
            ("draft", "รอค้นหาเอกสาร"),
            ("lines", "เลือกรายการเอกสาร"),
            ("done", "รับชำระเรียบร้อย"),
        ],
        string="สถานะ",
        default="draft",
        readonly=True,
        tracking=True,
    )
    generated_payment_ids = fields.Many2many(
        "account.payment",
        string="รายการชำระเงินที่สร้าง",
        readonly=True,
    )

    # --------------------------------------------------
    # Compute / onchange / constraints
    # --------------------------------------------------

    @api.depends("parent_partner_id")
    def _compute_group_root_partner(self):
        for wiz in self:
            wiz.group_root_partner_id = (
                wiz.parent_partner_id.commercial_partner_id
                if wiz.parent_partner_id
                else False
            )

    @api.onchange("parent_partner_id")
    def _onchange_parent_partner_id(self):
        """
        - root = commercial partner ของบริษัทที่เลือก
        - default ลูกค้า = ลูกทั้งหมดภายใต้ root (ยกเว้น root เอง)
        - ผู้จ่าย = root โดยอัตโนมัติ
        """
        if self.parent_partner_id:
            root = self.parent_partner_id.commercial_partner_id
            children = root.child_ids.filtered(
                lambda p: p.customer_rank > 0 and p.id != root.id
            )
            self.child_partner_ids = [(6, 0, children.ids)] if children else [(5, 0, 0)]
            self.payer_partner_id = root
        else:
            self.child_partner_ids = [(5, 0, 0)]
            self.payer_partner_id = False

    @api.onchange("payer_partner_id", "parent_partner_id", "child_partner_ids")
    def _onchange_payer_partner_id(self):
        """ผู้จ่ายต้องอยู่ในกลุ่ม root; ถ้าไม่อยู่ รีเซ็ตเป็น root และแจ้งเตือน"""
        if self.payer_partner_id and self.group_root_partner_id:
            allowed = self.group_root_partner_id | self.group_root_partner_id.child_ids
            if self.payer_partner_id not in allowed:
                self.payer_partner_id = self.group_root_partner_id
                return {
                    "warning": {
                        "title": _("ผู้จ่ายไม่อยู่ในกลุ่ม"),
                        "message": _("ระบบตั้งผู้จ่ายเป็นรากกลุ่ม (บริษัทแม่) ให้อัตโนมัติ"),
                    }
                }

    @api.depends("line_ids", "line_ids.is_selected", "line_ids.amount_to_pay")
    def _compute_total_selected_amount(self):
        for wiz in self:
            wiz.total_selected_amount = sum(
                line.amount_to_pay for line in wiz.line_ids if line.is_selected
            )

    @api.depends("line_ids", "line_ids.is_selected", "line_ids.amount_to_pay")
    def _compute_summary_info(self):
        for wiz in self:
            count = len(wiz.line_ids.filtered("is_selected"))
            amount_str = "{:,.2f}".format(wiz.total_selected_amount)
            symbol = wiz.currency_id.symbol or ""
            # Format: เลือก 1 รายการ, ยอดรวม 6,180.00 ฿
            wiz.summary_info = f"เลือก {count} รายการ, ยอดรวม {amount_str} {symbol}"

    # --------------------------------------------------
    # ดึงเอกสาร
    # --------------------------------------------------
    def _search_moves_internal(self):
        """ดึงใบแจ้งหนี้/เครดิตโน้ตค้างชำระตามเงื่อนไขและกรองอัตโนมัติ"""
        partners = (
            (self.group_root_partner_id | self.child_partner_ids)
            if self.group_root_partner_id
            else self.child_partner_ids
        )
        if not partners:
            return []
        Move = self.env["account.move"].with_company(self.company_id)
        domain = [
            ("move_type", "in", ["out_invoice", "out_refund"]),
            ("state", "=", "posted"),
            ("payment_state", "!=", "paid"),
            ("partner_id", "in", partners.ids),
            ("company_id", "=", self.company_id.id),
        ]
        if self.filter_date_from:
            domain.append(("invoice_date", ">=", self.filter_date_from))
        if self.filter_date_to:
            domain.append(("invoice_date", "<=", self.filter_date_to))
        moves = Move.search(domain, order="invoice_date asc, id asc")

        lines = []
        for mv in moves:
            residual = abs(mv.amount_residual)
            if not residual:
                continue
            if self.filter_min_amount and residual < self.filter_min_amount:
                continue
            lines.append(
                (
                    0,
                    0,
                    {
                        "move_id": mv.id,
                        "partner_id": mv.partner_id.id,
                        "currency_id": mv.currency_id.id,
                        "amount_total": abs(mv.amount_total),
                        "amount_residual": residual,
                        "amount_to_pay": residual,
                        "is_selected": True,
                    },
                )
            )
        return lines

    def action_search_moves(self):
        self.ensure_one()
        if not self.parent_partner_id:
            raise UserError(_("กรุณาเลือกบริษัทแม่ก่อนค้นหาเอกสาร"))
        lines = self._search_moves_internal()
        if not lines:
            raise UserError(_("ไม่พบใบแจ้งหนี้หรือเครดิตโน้ตที่ยังค้างชำระในกลุ่มนี้"))
        # Clear existing lines before adding new ones to avoid duplicates
        self.line_ids = [(5, 0, 0)] + lines
        self.state = "lines"

    # --------------------------------------------------
    # ตรวจสอบก่อนรับชำระ
    # --------------------------------------------------
    def _check_before_confirm(self):
        self.ensure_one()
        if not self.payer_partner_id:
            raise UserError(_("กรุณาเลือกว่าบริษัทใดเป็นผู้จ่าย"))
        if not self.payment_journal_id:
            raise UserError(_("กรุณาเลือกบัญชีธนาคารที่ใช้รับเงิน"))

        selected_lines = self.line_ids.filtered("is_selected")
        # กรองกรณีเอกสารถูกยกเลิก/ลบ/ชำระไปแล้วหลังจากค้นหา
        selected_lines = selected_lines.filtered(
            lambda l: l.move_id
            and l.move_id.exists()
            and l.move_id.state == "posted"
            and l.move_id.payment_state != "paid"
        )
        if not selected_lines:
            raise UserError(_("ไม่พบเอกสารที่ยังต้องรับชำระ กรุณาค้นหาเอกสารใหม่"))
        if self.total_selected_amount <= 0:
            raise UserError(_("ยอดรวมที่เลือกต้องมากกว่า 0"))

        move_ids = selected_lines.mapped("move_id").ids
        moves = self.env["account.move"].browse(move_ids).exists()
        if len(moves) != len(move_ids):
            # ลบบรรทัดที่อ้างอิงเอกสารหายไป
            missing_ids = set(move_ids) - set(moves.ids)
            for line in selected_lines:
                if line.move_id.id in missing_ids:
                    self.line_ids = [(2, line.id, 0)]
            raise UserError(_("เอกสารถูกยกเลิกหรือไม่พบแล้ว กรุณาค้นหาเอกสารใหม่"))
        # ตรวจสกุลเงินและบริษัทให้สอดคล้องกับ journal/company
        for mv in moves:
            if mv.company_id != self.company_id:
                raise UserError(_("เอกสาร %s อยู่คนละบริษัทกับ wizard นี้") % mv.name)
            if (
                self.payment_journal_id.currency_id
                and mv.currency_id != self.payment_journal_id.currency_id
            ):
                raise UserError(
                    _("เอกสาร %s สกุลเงิน %s ไม่ตรงกับสกุลเงินของสมุดเงินสด/ธนาคารที่เลือก")
                    % (mv.name, mv.currency_id.display_name)
                )

    # --------------------------------------------------
    # รับชำระเลย
    # --------------------------------------------------
    def action_confirm_payment(self):
        self.ensure_one()
        self._check_before_confirm()

        selected_lines = self.line_ids.filtered("is_selected")
        selected_lines = selected_lines.filtered(
            lambda l: l.move_id
            and l.move_id.exists()
            and l.move_id.state == "posted"
            and l.move_id.payment_state != "paid"
        )
        if not selected_lines:
            raise UserError(_("เอกสารถูกยกเลิก/ชำระแล้ว หรือไม่พบ กรุณาค้นหาเอกสารใหม่"))
        # รองรับ partial ต่อเอกสาร: จ่ายแยกเป็นรายการต่อใบ
        for line in selected_lines:
            if (
                line.amount_to_pay <= 0
                or line.amount_to_pay > line.amount_residual + 1e-6
            ):
                raise UserError(
                    _("ยอดที่จะรับชำระของ %s ต้องอยู่ระหว่าง 0 ถึงยอดคงค้าง") % line.move_id.name
                )

        payment_ids = []
        for line in selected_lines:
            move = line.move_id.with_company(self.company_id)
            if (not move.exists()) or move.payment_state == "paid":
                raise UserError(
                    _("เอกสาร %s ถูกลบ/ยกเลิก/ชำระไปแล้ว กรุณาค้นหาเอกสารใหม่") % move.name
                )

            # Find lines to pay (receivable/payable lines that are not reconciled)
            lines_to_pay = move.line_ids.filtered(
                lambda l: l.account_id.account_type
                in ("asset_receivable", "liability_payable")
                and not l.reconciled
            )

            if not lines_to_pay:
                raise UserError(_("ไม่พบรายการทางบัญชีที่ต้องชำระสำหรับเอกสาร %s") % move.name)

            pay_reg = (
                self.env["account.payment.register"]
                .with_company(self.company_id)
                .with_context(
                    active_model="account.move.line", active_ids=lines_to_pay.ids
                )
                .create(
                    {
                        "payment_date": self.payment_date,
                        "journal_id": self.payment_journal_id.id,
                        "amount": line.amount_to_pay,
                        # "communication": _("Group payment by %s") % self.payer_partner_id.display_name,
                        "line_ids": [(6, 0, lines_to_pay.ids)],
                    }
                )
            )
            payments = pay_reg._create_payments()

            # Update Group Payment Memo
            if self.memo:
                payments.write({'group_payment_memo': self.memo})

            payment_ids.extend(payments.ids)

        self.state = "done"
        self.generated_payment_ids = [(6, 0, payment_ids)]

        # Update lines to show 0 residual and 0 to pay
        for line in selected_lines:
            line.write(
                {
                    "amount_residual": 0.0,
                    "amount_to_pay": 0.0,
                }
            )

        # No need to reload wizard, just stay on the form
        return True

    def action_view_payments(self):
        self.ensure_one()
        return {
            "name": _("Payments"),
            "type": "ir.actions.act_window",
            "res_model": "account.payment",
            "view_mode": "list,form",
            "domain": [("id", "in", self.generated_payment_ids.ids)],
            "context": {"create": False},
        }

    def action_print_receipt(self):
        self.ensure_one()
        if not self.generated_payment_ids:
            raise UserError(_("ไม่พบรายการชำระเงินที่จะพิมพ์"))

        report_domain = [("model_id", "=", self._name)]
        found_report = self.env["jasper.report"].search(
            report_domain, order="id", limit=1
        )

        if not found_report:
            raise UserError(_("ไม่พบเอกสารที่จะพิมพ์"))

        report_result = found_report.run_report(self.generated_payment_ids.ids)

        return report_result

    def action_cancel_to_accounting(self):
        """ปิด Wizard แล้วกลับไปหน้า Accounting Dashboard"""
        return self.env.ref("account.open_account_journal_dashboard_kanban").read()[0]


class AccountCustomerGroupPaymentLine(models.Model):
    """รายการเอกสารใน wizard รับชำระเงินกลุ่มลูกค้า (แม่–ลูก)"""

    _name = "account.customer.group.payment.line"
    _description = "รายการเอกสาร - รับชำระเงินกลุ่มลูกค้า"

    payment_id = fields.Many2one(
        "account.customer.group.payment",
        string="Group Payment",
        required=True,
        ondelete="cascade",
    )
    move_id = fields.Many2one(
        "account.move",
        string="ใบแจ้งหนี้ / เครดิตโน้ต",
        required=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="ลูกค้า",
        required=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="สกุลเงิน",
        required=True,
    )
    amount_total = fields.Monetary(
        string="ยอดเต็มเอกสาร",
        currency_field="currency_id",
        readonly=True,
    )
    amount_residual = fields.Monetary(
        string="ยอดคงค้าง",
        currency_field="currency_id",
        readonly=True,
    )
    amount_to_pay = fields.Monetary(
        string="ยอดที่จะรับชำระ",
        currency_field="currency_id",
        readonly=False,
    )
    is_selected = fields.Boolean(
        string="เลือก",
        default=True,
    )
