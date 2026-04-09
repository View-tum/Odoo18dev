# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AccountGroupPaymentWizard(models.TransientModel):
    """
    Wizard: จ่ายบิลกลุ่มบริษัท (แม่–ลูก)

    Flow:
    - เลือกบริษัทแม่
    - เลือกบริษัทลูก (หลายบริษัทได้)
    - เลือกว่ารอบนี้ใครเป็นผู้จ่าย (แม่หรือลูกตัวไหน)
    - เลือกคู่ค้า (vendor)
    - เลือกธนาคารของบริษัทผู้จ่าย
    - ค้นหาบิล -> เลือก -> จ่ายเลย

    Logic:
    - บิลของบริษัทผู้จ่าย: ใช้ account.payment.register จ่ายปกติ
    - บิลของบริษัทอื่นในกลุ่ม: ทำ intercompany
      * ฝั่งบริษัทที่ถูกจ่ายแทน: JE เดบิต payable vendor / เครดิต intercompany payable
      * ฝั่งบริษัทผู้จ่าย: JE เดบิต intercompany receivable / เครดิต bank
    """

    _name = "account.group.payment.wizard"
    _description = "จ่ายบิลกลุ่มบริษัท (แม่–ลูก)"

    # กลุ่มบริษัท
    parent_company_id = fields.Many2one(
        "res.company",
        string="บริษัทแม่",
        required=True,
        default=lambda self: self.env.company,
        help="บริษัทแม่ของกลุ่มที่จะใช้สำหรับรอบนี้",
    )
    child_company_ids = fields.Many2many(
        "res.company",
        string="บริษัทลูก",
        help="บริษัทลูกในกลุ่ม (เลือกได้หลายบริษัท)",
    )

    payer_type = fields.Selection(
        [
            ("parent", "แม่เป็นผู้จ่าย"),
            ("child", "ลูกเป็นผู้จ่าย"),
        ],
        string="ใครเป็นผู้จ่าย",
        default="parent",
        required=True,
    )
    payer_child_company_id = fields.Many2one(
        "res.company",
        string="บริษัทลูกที่เป็นผู้จ่าย",
        help="กรณีเลือก 'ลูกเป็นผู้จ่าย' ให้เลือกว่าลูกตัวไหน",
    )
    payer_company_id = fields.Many2one(
        "res.company",
        string="บริษัทผู้จ่าย (ใช้จริง)",
        compute="_compute_payer_company_id",
        store=True,
    )

    # คู่ค้า
    partner_id = fields.Many2one(
        "res.partner",
        string="เจ้าหนี้ / คู่ค้า",
        required=True,
        help="เลือก Vendor / คู่ค้าที่ต้องการจ่ายในรอบนี้",
    )

    # การจ่ายเงิน
    payment_journal_id = fields.Many2one(
        "account.journal",
        string="บัญชีธนาคารที่ใช้จ่าย",
        domain="[('type', '=', 'bank'), ('company_id', '=', payer_company_id)]",
        required=True,
        help="ธนาคารของบริษัทผู้จ่าย",
    )
    payment_date = fields.Date(
        string="วันที่จ่าย",
        default=fields.Date.context_today,
        required=True,
    )

    # รายการบิล
    line_ids = fields.One2many(
        "account.group.payment.wizard.line",
        "wizard_id",
        string="รายการบิล",
    )

    state = fields.Selection(
        [
            ("draft", "รอค้นหาบิล"),
            ("lines", "เลือกรายการบิล"),
            ("done", "ทำการจ่ายเรียบร้อย"),
        ],
        string="สถานะ",
        default="draft",
        readonly=True,
    )
    total_selected_amount = fields.Monetary(
        string="ยอดรวมที่เลือก",
        compute="_compute_total_selected_amount",
        currency_field="payer_currency_id",
    )
    payer_currency_id = fields.Many2one(
        "res.currency",
        string="สกุลเงินของบริษัทผู้จ่าย",
        related="payer_company_id.currency_id",
        readonly=True,
    )

    # ------------------------------------------------------------------
    # Compute / onchange / constraints
    # ------------------------------------------------------------------
    @api.depends("payer_type", "parent_company_id", "payer_child_company_id")
    def _compute_payer_company_id(self):
        for wiz in self:
            if wiz.payer_type == "parent":
                wiz.payer_company_id = wiz.parent_company_id
            else:
                wiz.payer_company_id = wiz.payer_child_company_id

    @api.onchange("parent_company_id")
    def _onchange_parent_company_id(self):
        if self.parent_company_id and not self.child_company_ids:
            all_companies = self.env["res.company"].search([])
            children = all_companies - self.parent_company_id
            self.child_company_ids = [(6, 0, children.ids)]

    @api.onchange("payer_type", "child_company_ids")
    def _onchange_payer_type(self):
        if self.payer_type == "parent":
            self.payer_child_company_id = False
        else:
            if self.child_company_ids and not self.payer_child_company_id:
                self.payer_child_company_id = self.child_company_ids[0].id

    @api.constrains("payer_type", "parent_company_id", "payer_child_company_id")
    def _check_payer_company(self):
        for wiz in self:
            if wiz.payer_type == "parent":
                if not wiz.parent_company_id:
                    raise ValidationError(_("กรุณาเลือกบริษัทแม่ก่อน"))
            else:
                if not wiz.payer_child_company_id:
                    raise ValidationError(_("กรุณาเลือกบริษัทลูกที่เป็นผู้จ่าย"))

    @api.depends("line_ids", "line_ids.is_selected", "line_ids.amount_to_pay")
    def _compute_total_selected_amount(self):
        for wiz in self:
            wiz.total_selected_amount = sum(
                line.amount_to_pay for line in wiz.line_ids if line.is_selected
            )

    # ------------------------------------------------------------------
    # ค้นหาบิล (Bills เท่านั้น)
    # ------------------------------------------------------------------
    def action_search_bills(self):
        """
        ดึง Bills (in_invoice, in_refund) ของ partner_id ในบริษัทแม่ + บริษัทลูก
        เฉพาะที่ state=posted และยังไม่จ่ายเต็ม (payment_state != paid)
        """
        self.ensure_one()

        if not self.parent_company_id:
            raise UserError(_("กรุณาเลือกบริษัทแม่ก่อนค้นหาบิล"))

        companies = self.parent_company_id
        if self.child_company_ids:
            companies |= self.child_company_ids

        Move = self.env["account.move"]
        self.line_ids = [(5, 0, 0)]
        new_lines = []

        for company in companies:
            moves = Move.with_company(company).search(
                [
                    ("move_type", "in", ["in_invoice", "in_refund"]),
                    ("state", "=", "posted"),
                    ("payment_state", "!=", "paid"),
                    ("partner_id", "=", self.partner_id.id),
                ]
            )
            for mv in moves:
                residual = abs(mv.amount_residual)
                if not residual:
                    continue
                new_lines.append(
                    (
                        0,
                        0,
                        {
                            "move_id": mv.id,
                            "company_id": company.id,
                            "currency_id": mv.currency_id.id,
                            "amount_total": abs(mv.amount_total),
                            "amount_residual": residual,
                            "amount_to_pay": residual,
                            "is_selected": True,
                        },
                    )
                )

        if not new_lines:
            raise UserError(_("ไม่พบบิลของคู่ค้านี้ในบริษัทแม่/ลูกที่เลือก"))

        self.line_ids = new_lines
        self.state = "lines"
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.group.payment.wizard",
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
        }

    # ------------------------------------------------------------------
    # ตรวจสอบก่อนจ่าย
    # ------------------------------------------------------------------
    def _check_before_confirm(self):
        self.ensure_one()
        if not self.payer_company_id:
            raise UserError(_("ไม่พบบริษัทผู้จ่าย กรุณาตรวจสอบการตั้งค่าผู้จ่าย"))
        if not self.payment_journal_id:
            raise UserError(_("กรุณาเลือกบัญชีธนาคารของบริษัทผู้จ่าย"))
        if self.payment_journal_id.company_id != self.payer_company_id:
            raise UserError(_("บัญชีธนาคารต้องเป็นของบริษัทผู้จ่ายเท่านั้น"))

        selected_lines = self.line_ids.filtered("is_selected")
        if not selected_lines:
            raise UserError(_("กรุณาเลือกรายการบิลอย่างน้อย 1 รายการ"))
        if self.total_selected_amount <= 0:
            raise UserError(_("ยอดรวมที่เลือกต้องมากกว่า 0"))
        for line in selected_lines:
            if abs(line.amount_to_pay - line.amount_residual) > 1e-6:
                raise UserError(
                    _(
                        "ยังไม่รองรับการจ่ายบางส่วนต่อบิลในเวอร์ชันนี้\n"
                        "กรุณาให้ 'ยอดที่จะจ่าย' เท่ากับ 'ยอดคงค้าง' ทุกบิลก่อน"
                    )
                )

    # ------------------------------------------------------------------
    # จ่ายเลย
    # ------------------------------------------------------------------
    def action_confirm_payment(self):
        self.ensure_one()
        self._check_before_confirm()

        payer_company = self.payer_company_id
        selected_lines = self.line_ids.filtered("is_selected")

        payer_lines = selected_lines.filtered(lambda l: l.company_id == payer_company)
        other_lines = selected_lines.filtered(lambda l: l.company_id != payer_company)

        # 1) จ่ายบิลของบริษัทผู้จ่าย
        if payer_lines:
            payer_moves = payer_lines.mapped("move_id").with_company(payer_company)
            pay_reg = (
                self.env["account.payment.register"]
                .with_company(payer_company)
                .with_context(active_model="account.move", active_ids=payer_moves.ids)
                .create(
                    {
                        "payment_date": self.payment_date,
                        "journal_id": self.payment_journal_id.id,
                    }
                )
            )
            pay_reg.action_create_payments()

        # 2) จัดการบิลของบริษัทอื่น (แม่/ลูกจ่ายแทนกัน)
        if other_lines:
            if not payer_company.property_intercompany_receivable_id:
                raise UserError(
                    _("กรุณาตั้งค่า 'Intercompany Receivable' ให้บริษัทผู้จ่าย (%s) ก่อน")
                    % payer_company.display_name
                )
            parent_ic_recv = payer_company.property_intercompany_receivable_id
            payer_bank_account = self.payment_journal_id.default_account_id
            if not payer_bank_account:
                raise UserError(_("กรุณาตั้งค่า default account ให้บัญชีธนาคารของบริษัทผู้จ่าย"))
            if not payer_company.partner_id:
                raise UserError(
                    _(
                        "บริษัทผู้จ่าย (%s) ยังไม่มี Contact ผูกไว้ใน Company Form\n"
                        "กรุณาเลือก Contact เพื่อใช้กับ intercompany"
                    )
                    % payer_company.display_name
                )

            child_company_amount_map = {}

            for line in other_lines:
                company = line.company_id
                if not company.property_intercompany_payable_id:
                    raise UserError(
                        _("กรุณาตั้งค่า 'Intercompany Payable' ให้บริษัท %s ก่อน")
                        % company.display_name
                    )
                if not company.partner_id:
                    raise UserError(
                        _(
                            "บริษัท %s ยังไม่มี Contact ผูกไว้ใน Company Form\n"
                            "กรุณาเลือก Contact เพื่อใช้กับ intercompany"
                        )
                        % company.display_name
                    )

                child_ic_payable = company.property_intercompany_payable_id
                child_company_amount_map.setdefault(company, 0.0)
                child_company_amount_map[company] += line.amount_to_pay

                MoveChild = self.env["account.move"].with_company(company)
                invoice = line.move_id.with_company(company)
                payable_line = invoice.line_ids.filtered(
                    lambda l: l.account_id.internal_type == "payable"
                )[:1]
                if not payable_line:
                    raise UserError(_("ไม่พบบัญชีเจ้าหนี้ (payable) ในบิล %s") % invoice.name)

                je_child_vals = {
                    "move_type": "entry",
                    "date": self.payment_date,
                    "ref": _("บริษัท %s จ่ายแทน - %s")
                    % (payer_company.display_name, self.partner_id.display_name),
                    "line_ids": [
                        (
                            0,
                            0,
                            {
                                "name": _("ปิดบิล vendor (บริษัทอื่นจ่ายแทน)"),
                                "account_id": payable_line.account_id.id,
                                "debit": line.amount_to_pay,
                                "credit": 0.0,
                                "partner_id": self.partner_id.id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "name": _("ตั้งหนี้ข้ามบริษัท (ติด %s)") % payer_company.display_name,
                                "account_id": child_ic_payable.id,
                                "debit": 0.0,
                                "credit": line.amount_to_pay,
                                "partner_id": payer_company.partner_id.id,
                            },
                        ),
                    ],
                }
                je_child = MoveChild.create(je_child_vals)
                je_child.action_post()

                (invoice.line_ids + je_child.line_ids).filtered(
                    lambda l: l.account_id == payable_line.account_id
                ).reconcile()

            if child_company_amount_map:
                MoveParent = self.env["account.move"].with_company(payer_company)
                line_vals = []
                total_children = 0.0

                for child_company, amount in child_company_amount_map.items():
                    total_children += amount
                    line_vals.append(
                        (
                            0,
                            0,
                            {
                                "name": _("บริษัทย่อย %s - จ่ายแทน") % child_company.display_name,
                                "account_id": parent_ic_recv.id,
                                "debit": amount,
                                "credit": 0.0,
                                "partner_id": child_company.partner_id.id,
                            },
                        )
                    )

                line_vals.append(
                    (
                        0,
                        0,
                        {
                            "name": _("จ่ายแทนบริษัทลูก (รวม)"),
                            "account_id": payer_bank_account.id,
                            "debit": 0.0,
                            "credit": total_children,
                        },
                    )
                )

                je_parent_vals = {
                    "move_type": "entry",
                    "date": self.payment_date,
                    "ref": _("จ่ายแทนบริษัทลูกให้เจ้าหนี้ %s") % self.partner_id.display_name,
                    "line_ids": line_vals,
                }
                je_parent = MoveParent.create(je_parent_vals)
                je_parent.action_post()

        self.state = "done"
        return {"type": "ir.actions.act_window_close"}


class AccountGroupPaymentWizardLine(models.TransientModel):
    """รายการบิลใน wizard จ่ายบิลกลุ่มบริษัท"""

    _name = "account.group.payment.wizard.line"
    _description = "รายการบิล - จ่ายบิลกลุ่มบริษัท"

    wizard_id = fields.Many2one(
        "account.group.payment.wizard",
        string="Wizard",
        required=True,
        ondelete="cascade",
    )
    move_id = fields.Many2one(
        "account.move",
        string="บิลเจ้าหนี้",
        required=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="บริษัทของบิล",
        required=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="สกุลเงิน",
        required=True,
    )
    amount_total = fields.Monetary(
        string="ยอดเต็มบิล",
        currency_field="currency_id",
        readonly=True,
    )
    amount_residual = fields.Monetary(
        string="ยอดคงค้าง",
        currency_field="currency_id",
        readonly=True,
    )
    amount_to_pay = fields.Monetary(
        string="ยอดที่จะจ่าย",
        currency_field="currency_id",
    )
    is_selected = fields.Boolean(
        string="เลือก",
        default=True,
    )
