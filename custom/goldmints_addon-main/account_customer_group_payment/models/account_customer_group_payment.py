# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountCustomerGroupPayment(models.Model):
    _name = "account.customer.group.payment"
    _description = "รับชำระเงินกลุ่มบริษัท (Company Group)"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string="Name", compute="_compute_name", store=True)

    @api.depends("company_group_id")
    def _compute_name(self):
        for record in self:
            if record.company_group_id:
                record.name = _("Group Payment: %s") % record.company_group_id.name
            else:
                record.name = _("Group Payment")

    # Grouping Fields
    company_group_id = fields.Many2one(
        "res.partner",
        string="กลุ่มบริษัท (Company Group)",
        required=False,
        domain="['|', ('is_company_group', '=', True), ('company_group_id', '!=', False)]",
        help="เลือกกลุ่มบริษัทที่ต้องการรับชำระเงิน",
        tracking=True,
    )
    group_root_partner_id = fields.Many2one(
        "res.partner",
        string="กลุ่มบริษัท (Root)",
        compute="_compute_group_root_partner",
        store=True,
        readonly=True,
    )
    member_partner_ids = fields.Many2many(
        "res.partner",
        string="ลูกค้าที่เลือก",
        help="เลือกลูกค้าที่ต้องการรับชำระเงิน (เลือกได้หลายราย ไม่จำกัดกลุ่ม)",
    )
    is_select_all = fields.Boolean(
        default=True,
    )

    @api.onchange("is_select_all")
    def _onchange_is_select_all(self):
        for line in self.line_ids:
            line.is_selected = self.is_select_all

    payment_journal_id = fields.Many2one(
        "account.journal",
        string="บัญชีธนาคารที่ใช้รับเงิน",
        domain="[('type', 'in', ('bank', 'cash')), ('company_id', '=', company_id)]",
        required=False,
        help="สมุดเงินสด/ธนาคารของบริษัทเรา ใช้รับเงินจากลูกค้ากลุ่มนี้",
        tracking=True,
    )
    payment_date = fields.Date(
        string="วันที่จ่าย",
        default=fields.Date.context_today,
        required=False,
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

    @api.depends("company_group_id")
    def _compute_memo(self):
        for record in self:
            if record.company_group_id:
                record.memo = (
                    _("Group payment for %s") % record.company_group_id.display_name
                )
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

    def _get_group_root_partner(self):
        self.ensure_one()
        partner = self.company_group_id
        if partner and partner.company_group_id:
            return partner.company_group_id
        return partner

    @api.depends("company_group_id", "company_group_id.company_group_id")
    def _compute_group_root_partner(self):
        for wiz in self:
            wiz.group_root_partner_id = wiz._get_group_root_partner()

    @api.onchange("company_group_id")
    def _onchange_company_group_id(self):
        if self.company_group_id:
            selected_partner = self.company_group_id
            root_partner = self._get_group_root_partner()
            if root_partner and selected_partner != root_partner:
                self.company_group_id = root_partner
            members = self.env["res.partner"].search(
                [("company_group_id", "=", root_partner.id)]
            )
            self.member_partner_ids = [(6, 0, members.ids)] if members else [(5, 0, 0)]
            if root_partner and selected_partner != root_partner:
                return {
                    "warning": {
                        "title": _("Converted to Company Group"),
                        "message": _(
                            "You selected a member company. The system automatically switched to its company group."
                        ),
                    }
                }
        else:
            self.member_partner_ids = [(5, 0, 0)]
            self.line_ids = [(5, 0, 0)]
            self.state = "draft"

    @api.onchange("member_partner_ids")
    def _onchange_member_partner_ids(self):
        if self.member_partner_ids:
            lines = self._search_moves_internal()
            self.line_ids = [(5, 0, 0)] + lines if lines else [(5, 0, 0)]
            self.state = "lines" if lines else "draft"
        else:
            self.line_ids = [(5, 0, 0)]
            self.state = "draft"

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
        """ดึงใบแจ้งหนี้/เครดิตโน้ตค้างชำระตามสมาชิกที่เลือก"""
        partners = self.member_partner_ids
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
        if not self.member_partner_ids:
            raise UserError(_("กรุณาเลือกลูกค้าอย่างน้อย 1 รายก่อนค้นหาเอกสาร"))
        lines = self._search_moves_internal()
        if not lines:
            raise UserError(_("ไม่พบใบแจ้งหนี้หรือเครดิตโน้ตที่ยังค้างชำระสำหรับลูกค้าที่เลือก"))
        self.line_ids = [(5, 0, 0)] + lines
        self.state = "lines"

    # --------------------------------------------------
    # ตรวจสอบก่อนรับชำระ
    # --------------------------------------------------
    def _check_before_confirm(self):
        self.ensure_one()

        selected_lines = self.line_ids.filtered("is_selected")
        # กรองกรณีเอกสารถูกยกเลิก/ลบ/ชำระไปแล้วหลังจากค้นหา
        selected_lines = selected_lines.filtered(
            lambda line: (
                line.move_id
                and line.move_id.exists()
                and line.move_id.state == "posted"
                and line.move_id.payment_state != "paid"
            )
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

        currencies = selected_lines.mapped("move_id.currency_id")
        if len(currencies) > 1:
            raise UserError(
                _(
                    "กรุณาเลือกเอกสารสกุลเงินเดียวกันต่อหนึ่งครั้ง เพื่อให้เปิดหน้าชำระเงินแบบมาตรฐานของ Odoo ได้ถูกต้อง"
                )
            )

    # --------------------------------------------------
    # รับชำระ (เปิด Wizard มาตรฐาน)
    # --------------------------------------------------
    def action_confirm_payment(self):
        self.ensure_one()
        self._check_before_confirm()

        selected_lines = self.line_ids.filtered("is_selected")
        selected_moves = selected_lines.mapped("move_id").exists()
        # Collect receivable/payable lines from selected moves (used for validation only).
        move_line_ids = []
        for line in selected_lines:
            move = line.move_id
            lines_to_pay = move.line_ids.filtered(
                lambda line: (
                    line.account_id.account_type
                    in ("asset_receivable", "liability_payable")
                    and not line.reconciled
                )
            )
            move_line_ids.extend(lines_to_pay.ids)

        if not move_line_ids:
            raise UserError(_("ไม่พบรายการทางบัญชีที่ต้องชำระสำหรับเอกสารที่เลือก"))

        # No longer setting state to 'done' here.
        # The state will be updated by the payment registration wizard once payments are created.

        action_ctx = {
            "active_model": "account.move",
            "active_ids": selected_moves.ids,
            "is_group_payment": True,
            "group_payment": True,
            "default_group_payment": True,
            "default_company_group_id": self.group_root_partner_id.id
            if self.group_root_partner_id
            else False,
            "default_group_payment_id": self.id,
            "default_communication": self.memo,
            "default_payment_date": self.payment_date,
            "default_journal_id": self.payment_journal_id.id
            if self.payment_journal_id
            else False,
            "group_payment_move_line_ids": move_line_ids,
            "group_payment_amounts_by_move_id": {
                line.move_id.id: line.amount_to_pay for line in selected_lines
            },
        }

        # Pre-create the transient record server-side so all inherited default_get /
        # compute / onchange logic stabilizes before the web client renders the form.
        wizard = (
            self.env["account.payment.register"].with_context(**action_ctx).create({})
        )
        if (
            not wizard.line_ids
            or not wizard.currency_id
            or wizard.currency_id.is_zero(wizard.amount)
        ):
            raise UserError(
                _(
                    "Unable to prepare the payment wizard from the selected documents. "
                    "Please check selected invoices, journal currency, and manual exchange/WHT settings."
                )
            )

        return {
            "name": _("Pay"),
            "type": "ir.actions.act_window",
            "res_model": "account.payment.register",
            "view_mode": "form",
            "target": "new",
            "res_id": wizard.id,
            "context": action_ctx,
        }

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
