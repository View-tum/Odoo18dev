# -*- coding: utf-8 -*-
from odoo import models, fields, api, Command
from dateutil.relativedelta import relativedelta
from datetime import datetime, time


class SaleAnalysisReport(models.TransientModel):
    _name = "sale.analysis.report"
    _description = "Sale Analysis Report"

    line_ids = fields.One2many(
        "sale.analysis.report.line", "wizard_id", string="Report Lines"
    )

    filter_by = fields.Selection(
        selection=[
            ("salesperson", "Salesperson"),
            ("product", "Product"),
            ("customer", "Customer"),
            ("market_region", "Sales Zone"),
            ("top_ten", "Top 10 Best-Selling Products"),
        ],
        string="Filter by",
        default="salesperson",
        help="(365 custom) Select the criteria to filter the sales analysis report.",
    )

    sale_region_id = fields.Many2one(
        comodel_name="delivery.sales.region",
        string="Sales Region",
        help="(365 custom) Select a sales region to filter salespersons in the report.",
    )
    state_id = fields.Many2one(
        comodel_name="res.country.state",
        string="Province/State",
        domain="[('country_id.code', '=', 'TH')]",
        help="(365 custom) Select a province/state to filter salespersons based on their location. Only applicable for Thailand.",
    )

    team_id = fields.Many2one(
        comodel_name="crm.team",
        string="Sales Team",
        help="(365 custom) Select a sales team to filter salespersons in the report.",
    )

    salesperson_ids = fields.Many2many(
        comodel_name="res.users",
        string="Salespersons",
        domain="[('sale_team_id', '=', team_id), ('share', '=', False)] if team_id else []",
        help="(365 custom) Select specific salespersons to include in the report. If left empty, all salespersons will be considered.",
    )

    is_commission_confirmed = fields.Boolean(
        string="Confirm Commission",
        help="Check to confirm commission calculation/payment.",
        default=False,
    )

    partner_ids = fields.Many2many(
        comodel_name="res.partner",
        string="Customers",
        domain=[("customer_rank", ">", 0)],
        help="(365 custom) Select specific customers to include in the report.",
    )

    product_category_id = fields.Many2one(
        comodel_name="product.category",
        string="Product Category",
        help="(365 custom) Select a product category to filter products in the report.",
    )
    product_ids = fields.Many2many(
        comodel_name="product.product",
        domain=[("sale_ok", "=", True)],
        string="Products",
        help="(365 custom) Select specific products to include in the report. If left empty, all products will be considered.",
    )

    market_scope = fields.Selection(
        selection=[
            ("all", "All"),
            ("domestic", "Domestic"),
            ("inter", "International"),
        ],
        string="Sales Zone",
        default="all",
        help="(365 custom) Specify whether this type is for Domestic or International sales.",
    )

    def _get_year_selection(self):
        current_year = fields.Date.today().year
        return [(str(y), str(y)) for y in range(current_year - 5, current_year + 5)]

    select_year = fields.Selection(
        selection=_get_year_selection,
        string="Select Year",
        default=lambda self: str(fields.Date.today().year),
        help="(365 custom) Select year to auto-fill Date From and Date To.",
    )

    select_month = fields.Selection(
        [
            ("1", "January"),
            ("2", "February"),
            ("3", "March"),
            ("4", "April"),
            ("5", "May"),
            ("6", "June"),
            ("7", "July"),
            ("8", "August"),
            ("9", "September"),
            ("10", "October"),
            ("11", "November"),
            ("12", "December"),
        ],
        string="Select Month",
        help="(365 custom) Select a month to auto-fill Date From and Date To.",
    )

    date_from = fields.Date(
        string="Start Date",
        help="(365 custom) The start date for the report's data range.",
    )
    date_to = fields.Date(
        string="End Date", help="(365 custom) The end date for the report's data range."
    )
    report_id = fields.Many2one(
        comodel_name="jasper.report",
        string="Report",
        help="(365 custom) Select the Report template to be used for this summary.",
    )

    @api.model
    def default_get(self, fields_list):
        """
        This method is executed every time the Wizard is opened (Target: new).
        We use this opportunity to delete old Line data for that user.
        """

        res = super(SaleAnalysisReport, self).default_get(fields_list)

        if "date_to" in fields_list and not res.get("date_to"):
            res["date_to"] = fields.Date.context_today(self)

        if "date_from" in fields_list and not res.get("date_from"):
            res["date_from"] = fields.Date.context_today(self).replace(day=1)

        return res

    @api.onchange("filter_by")
    def _onchange_filter_by(self):
        if self.filter_by:
            self.sale_region_id = False
            self.state_id = [Command.clear()]
            self.salesperson_ids = [Command.clear()]
            self.product_category_id = False
            self.product_ids = [Command.clear()]
            self.partner_ids = [Command.clear()]
            self.line_ids = [Command.clear()]
            self.is_commission_confirmed = False
            config = self.env["sale.analysis.report.config"].search(
                [("filter_by", "=", self.filter_by)], limit=1
            )
            if config:
                self.report_id = config.report_id.id
            else:
                self.report_id = False

    @api.onchange("sale_region_id")
    def _onchange_sale_region_id(self):
        if self.sale_region_id:
            self.state_id = [Command.clear()]

    @api.onchange("team_id")
    def _onchange_team_id(self):
        """เมื่อเปลี่ยนทีมขาย ให้ล้างค่าพนักงานขายที่เคยเลือกไว้"""
        if self.team_id:
            self.salesperson_ids = [Command.clear()]

    @api.onchange("select_month", "select_year")
    def _onchange_period(self):
        if self.select_year and self.select_month:
            try:
                year = int(self.select_year)
                month = int(self.select_month)
                first_date = fields.Date.today().replace(year=year, month=month, day=1)
                last_date = first_date + relativedelta(months=1, days=-1)
                self.date_from = first_date
                self.date_to = last_date
            except ValueError:
                pass

    def _get_so_exchange_rate(self, so):
        """
        ฟังก์ชันช่วยคำนวณอัตราแลกเปลี่ยนของ Sale Order ใบนั้นๆ
        Return: อัตราแลกเปลี่ยน (Float) เพื่อแปลงเป็น THB (Company Currency)
        """
        company_currency = self.env.company.currency_id
        so_currency = so.currency_id
        so_date = so.date_order or fields.Date.context_today(self)

        if so_currency == company_currency:
            return 1.0
        if getattr(so, "sale_manual_currency_rate", False):
            return so.sale_manual_currency_rate
        return so_currency._get_conversion_rate(
            so_currency, company_currency, self.env.company, so_date
        )

    def _get_real_so_amount(self, so):
        """
        คำนวณยอดขายจริงของ SO โดยตัดยอด Down Payment ออก
        ป้องกันปัญหายอดเฟ้อ (Double Counting) ในรายงาน
        """
        # กรองเอาเฉพาะบรรทัดที่ไม่ใช่ Down Payment
        real_lines = so.order_line.filtered(lambda l: not l.is_downpayment)

        # รวมยอด (กรณี Multi-currency ต้อง convert ด้วย แต่ในที่นี้เราเอา base currency ของ SO ก่อน)
        amount = sum(real_lines.mapped("price_subtotal"))

        # แปลงเป็น THB (ตาม Logic เดิม)
        exchange_rate = self._get_so_exchange_rate(so)
        return amount * exchange_rate

    def _get_date_order_domain(self, field_prefix=""):
        """
        แปลง date_to ให้เป็นวันถัดไป แล้วใช้เครื่องหมาย <
        เพื่อให้ครอบคลุมเวลา 23:59:59 ของวันสิ้นสุด
        """
        self.ensure_one()

        # แปลง Date object ให้เป็น DateTime ที่เวลา 00:00:00
        dt_from = datetime.combine(self.date_from, time.min)
        dt_to = datetime.combine(self.date_to, time.min) + relativedelta(days=1)

        complete_name = f"{field_prefix}date_order"

        return [
            (complete_name, ">=", dt_from),
            (complete_name, "<", dt_to),
        ]

    def _get_region_domain(self, field_prefix=""):
        """
        สร้าง Domain สำหรับ Sales Region แบบ Dynamic
        :param field_prefix: เช่น 'order_id.' หาก search จาก line
        """
        self.ensure_one()
        domain = []
        if self.sale_region_id:
            region_field = f"{field_prefix}partner_id.salesregion_id"
            domain.append((region_field, "=", self.sale_region_id.id))
        if self.state_id:
            state_field = f"{field_prefix}partner_id.state_id"
            domain.append((state_field, "in", self.state_id.ids))
        return domain

    def _get_commission_mode_data(self, salesperson_id):
        """
        Sub-Method 1: Logic สำหรับโหมดคำนวณ Commission
        - เน้น Transaction จริง (Invoice/Payment) ในช่วงเวลา
        - กรองเฉพาะที่มี SO
        - แยกบรรทัด (1 Inv = 1 Line) เพื่อความชัดเจนในการจ่าย
        """
        sale_orders_data = []

        # เตรียม Config Commission
        commission_rate = 0.0
        commission_trigger_type = "invoice_confirmed"

        if salesperson_id.salesregion_id:
            commission_rule = self.env["sale.commission.rule"].search(
                [("region_ids", "in", salesperson_id.salesregion_id.id)], limit=1
            )
            if commission_rule and commission_rule.rate_id:
                commission_rate = commission_rule.rate_id.value
                commission_trigger_type = commission_rule.commission_trigger

        # --- PATH A: Sale กรุงเทพ (Trigger: Invoice Confirm) ---
        if commission_trigger_type == "invoice_confirmed":
            move_domain = [
                ("move_type", "in", ["out_invoice", "out_refund"]),
                ("state", "=", "posted"),
                ("invoice_date", ">=", self.date_from),
                ("invoice_date", "<=", self.date_to),
                ("invoice_user_id", "=", salesperson_id.id),
            ]
            if self.state_id:
                move_domain.append(("partner_id.state_id", "in", self.state_id.ids))
            moves = self.env["account.move"].search(move_domain)

            for move in moves:
                # [Rule] ต้องมี SO เท่านั้น
                so = move.invoice_line_ids.sale_line_ids.order_id
                if not so:
                    continue
                so = so[0]

                exchange_rate = self._get_so_exchange_rate(so)
                amount_thb = move.amount_untaxed * exchange_rate

                is_refund = move.move_type == "out_refund"
                if is_refund:
                    amount_thb = -abs(amount_thb)

                # Calc Commission
                comm_amount = amount_thb * (commission_rate / 100.0)
                real_so_amt = self._get_real_so_amount(so)
                payment_val = 0.0
                if move.amount_total and move.amount_total != 0:
                    # คำนวณสัดส่วนที่จ่ายแล้ว (Paid Ratio)
                    ratio = (
                        move.amount_total - move.amount_residual
                    ) / move.amount_total
                    # คูณสัดส่วนกับยอด Untaxed THB ที่คำนวณไว้
                    payment_val = amount_thb * ratio

                sale_orders_data.append(
                    {
                        "salesperson_id": salesperson_id.id,
                        "sale_order_name": so.name,
                        "customer_name": move.partner_id.name,
                        "invoice_name": move.name if not is_refund else "",
                        "credit_note_name": move.name if is_refund else "",
                        "amount_sale_total": real_so_amt,
                        "amount_invoice_total": (
                            amount_thb if not is_refund else 0.0
                        ),  # ถ้าเป็น Inv ใส่ช่อง Inv
                        "amount_credit_note_total": amount_thb if is_refund else 0.0,
                        "amount_payment_total": payment_val,
                        "amount_commission_total": comm_amount,
                    }
                )

        # --- PATH B: Sale ต่างจังหวัด (Trigger: Payment/Paid) ---
        elif commission_trigger_type == "invoice_paid":
            # ค้นหาการจับคู่ยอด (Partial Reconcile) ทั้งขาเข้า (Inv) และขาออก (Refund)
            reconcile_domain = [
                ("max_date", ">=", self.date_from),
                ("max_date", "<=", self.date_to),
                "|",
                # Case 1: จ่ายชำระ Invoice (De: Inv, Cr: Bank)
                "&",
                "&",
                "&",
                ("debit_move_id.move_id.move_type", "=", "out_invoice"),
                ("debit_move_id.move_id.invoice_user_id", "=", salesperson_id.id),
                ("credit_move_id.journal_id.type", "in", ["bank", "cash"]),
                ("debit_move_id.move_id.state", "=", "posted"),
                # Case 2: จ่ายคืน Refund/CN (Cr: CN, De: Bank)
                "&",
                "&",
                "&",
                ("credit_move_id.move_id.move_type", "=", "out_refund"),
                ("credit_move_id.move_id.invoice_user_id", "=", salesperson_id.id),
                ("debit_move_id.journal_id.type", "in", ["bank", "cash"]),
                ("credit_move_id.move_id.state", "=", "posted"),
            ]
            if self.state_id:
                reconcile_domain += [
                    "|",
                    "&",
                    ("debit_move_id.move_id.move_type", "=", "out_invoice"),
                    (
                        "debit_move_id.move_id.partner_id.state_id",
                        "in",
                        self.state_id.ids,
                    ),
                    "&",
                    ("credit_move_id.move_id.move_type", "=", "out_refund"),
                    (
                        "credit_move_id.move_id.partner_id.state_id",
                        "in",
                        self.state_id.ids,
                    ),
                ]
            partials = self.env["account.partial.reconcile"].search(reconcile_domain)

            for rec in partials:
                # ตรวจสอบว่าเป็นเคส รับชำระ หรือ คืนเงิน
                if rec.debit_move_id.move_id.move_type == "out_invoice":
                    # --- Case 1: รับชำระ Invoice ---
                    doc = rec.debit_move_id.move_id  # Invoice
                    sign = 1.0
                    inv_col_name = doc.name
                    cn_col_name = ""
                else:
                    # --- Case 2: จ่ายคืน Refund (CN) ---
                    doc = rec.credit_move_id.move_id  # Credit Note
                    sign = -1.0
                    inv_col_name = ""
                    cn_col_name = doc.name

                # [Rule] ต้องมี SO เท่านั้น
                so = doc.invoice_line_ids.sale_line_ids.order_id
                if not so:
                    continue
                so = so[0]

                exchange_rate = self._get_so_exchange_rate(so)
                real_so_amt = self._get_real_so_amount(so)

                # 1. ยอดที่รับชำระ/จ่ายคืนจริง (Collection)
                paid_amount_thb = rec.amount * sign

                paid_amount_untaxed_thb = paid_amount_thb / 1.07

                # 2. Commission
                comm_amount = paid_amount_untaxed_thb * (commission_rate / 100.0)
                # comm_amount = paid_amount_thb * (commission_rate / 100.0)

                # 3. ยอดอ้างอิง (แสดงเต็มใบ)
                amount_doc_thb = doc.amount_untaxed * exchange_rate * sign

                sale_orders_data.append(
                    {
                        "salesperson_id": salesperson_id.id,
                        "sale_order_name": so.name,
                        "customer_name": doc.partner_id.name,
                        "invoice_name": inv_col_name,
                        "credit_note_name": cn_col_name,
                        "amount_sale_total": real_so_amt,
                        "amount_invoice_total": amount_doc_thb if sign > 0 else 0.0,
                        "amount_credit_note_total": amount_doc_thb if sign < 0 else 0.0,
                        "amount_payment_total": paid_amount_thb,
                        "amount_commission_total": comm_amount,
                    }
                )

        return sale_orders_data

    def _get_analysis_mode_data(self, salesperson_id):
        """
        Sub-Method 2: Logic สำหรับโหมด Sales Analysis
        - เน้นภาพรวมการขาย (Performance)
        - รวมบรรทัด (1 SO = 1 Line)
        - แสดงยอด Invoice แบบ Gross (ไม่หัก CN)
        - แยกยอด CN ต่างหาก
        """
        sale_orders_data = []

        domain = (
            [("user_id", "=", salesperson_id.id)]
            + self._get_date_order_domain()
            + [("state", "in", ["sale", "done"])]
        )
        if self.state_id:
            domain += [("partner_id.state_id", "in", self.state_id.ids)]

        orders = self.env["sale.order"].search(domain, order="date_order, name")

        for so in orders:
            exchange_rate = self._get_so_exchange_rate(so)

            # หาเอกสารที่เกี่ยวข้อง
            invoices = so.invoice_ids.filtered(
                lambda m: m.state == "posted" and m.move_type == "out_invoice"
            )
            refunds = so.invoice_ids.filtered(
                lambda m: m.state == "posted" and m.move_type == "out_refund"
            )

            # 1. เตรียมชื่อเอกสาร
            inv_names_str = ",".join(invoices.mapped("name"))
            cn_names_str = ",".join(refunds.mapped("name"))

            # 2. คำนวณยอด Invoice (Gross Amount - ไม่หัก CN)
            acc_inv_amount = sum(invoices.mapped("amount_untaxed")) * exchange_rate

            # 3. คำนวณยอด CN (แยกต่างหากและเป็นยอดติดลบ)
            acc_cn_amount = sum(refunds.mapped("amount_untaxed")) * exchange_rate
            acc_cn_amount = -abs(acc_cn_amount)

            # 4. คำนวณยอด Payment (ยอดเก็บเงินจริง - ต้องคำนวณตามสัดส่วน)
            acc_pay = 0.0
            all_moves = invoices | refunds
            for m in all_moves:
                amt = m.amount_untaxed * exchange_rate
                if m.move_type == "out_refund":
                    amt = -abs(amt)

                if m.amount_total and m.amount_total != 0:
                    ratio = (m.amount_total - m.amount_residual) / m.amount_total
                    acc_pay += amt * ratio

            real_so_amt = self._get_real_so_amount(so)

            sale_orders_data.append(
                {
                    "salesperson_id": salesperson_id.id,
                    "sale_order_name": so.name,
                    "customer_name": so.partner_id.name,
                    "invoice_name": inv_names_str,
                    "credit_note_name": cn_names_str,
                    "amount_sale_total": real_so_amt,
                    "amount_invoice_total": acc_inv_amount,  # ยอด Gross
                    "amount_credit_note_total": acc_cn_amount,  # ยอด CN
                    "amount_payment_total": acc_pay,
                    "amount_commission_total": 0.0,
                }
            )

        return sale_orders_data

    def _prepare_single_salesperson_data(self, salesperson_id):
        """
        Main Method: ควบคุมการเลือก Logic ตาม Configuration
        """
        self.ensure_one()

        # 1. เลือกชุดข้อมูลตามโหมด (Strategy Pattern)
        if self.is_commission_confirmed:
            sale_orders_data = self._get_commission_mode_data(salesperson_id)
        else:
            sale_orders_data = self._get_analysis_mode_data(salesperson_id)

        # 2. Sort ข้อมูลเพื่อความสวยงาม
        sale_orders_data.sort(key=lambda x: x["sale_order_name"] or "")

        # 3. คืนค่าในรูปแบบมาตรฐาน (Standard Format)
        return {
            "company_name": self.env.company.name,
            "salesperson_id": salesperson_id.id,
            "sale_orders": sale_orders_data,
            "date_from": self.date_from.strftime("%d/%m/%Y"),
            "date_to": self.date_to.strftime("%d/%m/%Y"),
            "date_today": fields.Date.today().strftime("%d/%m/%Y"),
            "salesperson_name": salesperson_id.name,
            "region_name": (
                salesperson_id.salesregion_id.name
                if salesperson_id.salesregion_id
                else "-"
            ),
        }

    def _prepare_single_customer_data(self, partner_id):
        self.ensure_one()

        domain = [
            ("state", "in", ["sale", "done"]),
            ("amount_untaxed", "!=", 0),
        ]

        domain += self._get_date_order_domain(field_prefix="")

        if partner_id:
            domain += [("partner_id", "=", partner_id.id)]

        if self.sale_region_id:
            domain += self._get_region_domain()

        sale_orders = self.env["sale.order"].search(domain, order="date_order asc")

        # Logic การคำนวณเงิน
        so_invoice_map = {}
        if sale_orders:
            all_invoices = self.env["account.move"].search(
                [
                    ("invoice_line_ids.sale_line_ids.order_id", "in", sale_orders.ids),
                    ("state", "=", "posted"),
                    ("move_type", "in", ["out_invoice", "out_refund"]),
                ]
            )
            for inv in all_invoices:
                related_so_ids = inv.invoice_line_ids.sale_line_ids.order_id.ids
                for so_id in related_so_ids:
                    if so_id in sale_orders.ids:
                        if so_id not in so_invoice_map:
                            so_invoice_map[so_id] = self.env["account.move"]
                        so_invoice_map[so_id] |= inv

        customer_sales_data = []

        for so in sale_orders:
            exchange_rate = self._get_so_exchange_rate(so)
            all_invoices = so_invoice_map.get(so.id, self.env["account.move"])

            amount_sale = self._get_real_so_amount(so)

            # ยอด Invoice / Credit Note
            posted_invoices = all_invoices.filtered(
                lambda m: m.move_type == "out_invoice"
            )
            credit_notes = all_invoices.filtered(lambda m: m.move_type == "out_refund")

            amount_invoice_foreign = sum(posted_invoices.mapped("amount_untaxed"))
            amount_invoice = amount_invoice_foreign * exchange_rate

            amount_credit_foreign = sum(credit_notes.mapped("amount_untaxed"))
            amount_credit = -abs(amount_credit_foreign * exchange_rate)

            # ยอดรับชำระ (Payment)
            paid_invoices_only = posted_invoices.filtered(
                lambda inv: inv.payment_state in ["paid", "in_payment", "partial"]
            )

            amount_payment_foreign = 0.0
            for inv in paid_invoices_only:
                if inv.amount_total and inv.amount_total != 0:
                    paid_amount_taxed = inv.amount_total - inv.amount_residual
                    # หาสัดส่วน Untaxed
                    paid_amount_untaxed = paid_amount_taxed * (
                        inv.amount_untaxed / inv.amount_total
                    )
                    amount_payment_foreign += paid_amount_untaxed

            amount_payment = amount_payment_foreign * exchange_rate

            inv_names = ", \n".join(posted_invoices.mapped("name"))
            cn_names = ", \n".join(credit_notes.mapped("name"))

            customer_sales_data.append(
                {
                    "sale_order_name": so.name,
                    "salesperson_name": so.user_id.name,
                    "invoice_name": inv_names,
                    "credit_note_name": cn_names,
                    "amount_sale_total": amount_sale,
                    "amount_invoice_total": amount_invoice,
                    "amount_credit_note_total": amount_credit,
                    "amount_payment_total": max(amount_payment + amount_credit, 0.0),
                }
            )

        date_from = self.date_from.strftime("%d/%m/%Y")
        date_to = self.date_to.strftime("%d/%m/%Y")
        date_today = fields.Date.today().strftime("%d/%m/%Y")

        return {
            "company_name": self.env.company.name,
            "partner_id": partner_id.id,
            "customer_name": partner_id.name,
            "customer_sales_data": customer_sales_data,
            "date_from": date_from,
            "date_to": date_to,
            "date_today": date_today,
        }

    def _prepare_single_product_data(self, product_id):
        self.ensure_one()

        domain = [
            ("product_id", "=", product_id.id),
            ("state", "in", ["sale", "done"]),
            ("order_id.amount_untaxed", ">", 0),
            ("price_subtotal", ">=", 0),
            ("product_uom_qty", ">", 0),
        ]
        domain += self._get_date_order_domain(field_prefix="order_id.")

        if self.sale_region_id:
            domain += self._get_region_domain(field_prefix="order_id.")

        lines = self.env["sale.order.line"].search(domain, order="order_id asc")

        product_sales_data = []
        so_rate_cache = {}

        for line in lines:
            so = line.order_id

            if so.id in so_rate_cache:
                exchange_rate = so_rate_cache[so.id]
            else:
                exchange_rate = self._get_so_exchange_rate(so)
                so_rate_cache[so.id] = exchange_rate

            amount_untaxed = line.price_subtotal * exchange_rate

            product_sales_data.append(
                {
                    "sale_order_name": so.name,
                    "customer_name": so.partner_id.name,
                    "salesperson_id": so.user_id.id,
                    "quantity": line.product_uom_qty,
                    "amount_untaxed": amount_untaxed,
                }
            )

        date_from = self.date_from.strftime("%d/%m/%Y")
        date_to = self.date_to.strftime("%d/%m/%Y")
        date_today = fields.Date.today().strftime("%d/%m/%Y")

        product_category_name = (
            product_id.categ_id.display_name if product_id.categ_id else ""
        )

        return {
            "company_name": self.env.company.name,
            "product_id": product_id.id,
            "product_name": product_id.display_name,
            "product_category_name": product_category_name,
            "product_sales_data": product_sales_data,
            "date_from": date_from,
            "date_to": date_to,
            "date_today": date_today,
        }

    def _prepare_single_market_region_data(self):
        self.ensure_one()

        domain = [
            ("state", "in", ["sale", "done"]),
            ("price_subtotal", ">", 0),
            ("product_id.product_tmpl_id.type", "in", ["consu"]),
        ]
        domain += self._get_date_order_domain(field_prefix="order_id.")

        if self.market_scope and self.market_scope != "all":
            domain.append(("order_id.so_type_id.market_scope", "=", self.market_scope))
        elif self.market_scope == "all":
            domain.append(
                ("order_id.so_type_id.market_scope", "in", ["domestic", "inter"])
            )

        lines = self.env["sale.order.line"].search(domain, order="order_id asc")

        market_data = []

        so_rate_cache = {}

        for line in lines:
            so = line.order_id

            if so.id in so_rate_cache:
                exchange_rate = so_rate_cache[so.id]
            else:
                exchange_rate = self._get_so_exchange_rate(so)
                so_rate_cache[so.id] = exchange_rate

            amount_foreign = line.price_subtotal
            amount_thb = amount_foreign * exchange_rate

            product_name = line.product_id.name

            market_data.append(
                {
                    "sale_order_name": so.name,
                    "customer_name": so.partner_id.name,
                    "product_name": product_name,
                    "quantity": line.product_uom_qty,
                    "currency_name": so.currency_id.name,
                    "exchange_rate": exchange_rate,
                    "amount_foreign": amount_foreign,
                    "amount_thb": amount_thb,
                    "salesperson_id": so.user_id.id,
                }
            )

        date_from = self.date_from.strftime("%d/%m/%Y")
        date_to = self.date_to.strftime("%d/%m/%Y")
        date_today = fields.Date.today().strftime("%d/%m/%Y")

        market_scope_label = dict(self._fields["market_scope"].selection).get(
            self.market_scope, "All"
        )

        return {
            "company_name": self.env.company.name,
            "report_title": f"Sales Report by Zone - {market_scope_label}",
            "market_region_data": market_data,
            "date_from": date_from,
            "date_to": date_to,
            "date_today": date_today,
        }

    def _prepare_top_ten_data(self):
        self.ensure_one()
        domain = [
            ("state", "in", ["sale", "done"]),
            ("product_id.product_tmpl_id.type", "=", "consu"),
            ("is_downpayment", "=", False),
        ]
        domain += self._get_date_order_domain(field_prefix="order_id.")

        if self.sale_region_id:
            domain += self._get_region_domain(field_prefix="order_id.")

        lines = self.env["sale.order.line"].search(domain)

        product_stats = {}
        so_rate_cache = {}

        for line in lines:
            so = line.order_id
            product = line.product_id

            if so.id in so_rate_cache:
                exchange_rate = so_rate_cache[so.id]
            else:
                exchange_rate = self._get_so_exchange_rate(so)
                so_rate_cache[so.id] = exchange_rate

            amount_thb = line.price_subtotal * exchange_rate
            qty = line.product_uom_qty

            if product.id not in product_stats:
                product_stats[product.id] = {
                    "product_name": product.display_name,
                    "quantity": 0.0,
                    "amount": 0.0,
                }

            product_stats[product.id]["quantity"] += qty
            product_stats[product.id]["amount"] += amount_thb

        parsed_groups = [
            stats
            for stats in product_stats.values()
            if stats["quantity"] > 0 and stats["amount"] > 0
        ]

        sorted_qty = sorted(parsed_groups, key=lambda x: x["quantity"], reverse=True)[
            :10
        ]
        sorted_amount = sorted(parsed_groups, key=lambda x: x["amount"], reverse=True)[
            :10
        ]

        return {
            "top_qty": sorted_qty,
            "top_amount": sorted_amount,
        }

    def _get_report_filename(self):
        self.ensure_one()
        date_str = fields.Date.today().strftime("%Y-%m-%d")

        if self.sale_region_id:
            region_name = self.sale_region_id.name
            report_name = f"Sales Report - {region_name}"
        else:
            report_name = "Sales Report – All Regions"

        if self.filter_by == "salesperson":
            if self.salesperson_ids:
                names = self.salesperson_ids.mapped("name")
                salesman_name = names[0] if len(names) == 1 else "Many Salespeople"
                report_name = f"{report_name} - {salesman_name}"

        elif self.filter_by == "product":
            if self.product_ids:
                names = self.product_ids.mapped("name")
                product_name = names[0] if len(names) == 1 else "Many Products"
                report_name = f"{report_name} - {product_name}"

            elif self.product_category_id:
                category_name = self.product_category_id.name
                report_name = f"{report_name} - {category_name}"

        elif self.filter_by == "customer":
            if self.partner_ids:
                names = self.partner_ids.mapped("name")
                cust_name = names[0] if len(names) == 1 else "Many Customers"
                report_name = f"{report_name} - {cust_name}"
            else:
                report_name = f"{report_name} - All Customers"

        elif self.filter_by == "market_region":
            scope_label = dict(self._fields["market_scope"].selection).get(
                self.market_scope, ""
            )
            report_name = f"Sales Report - {scope_label}"

        elif self.filter_by == "top_ten":
            report_name = f"{report_name} - Top 10 Best-Selling Products"

        if self.is_commission_confirmed:
            report_name = f"{report_name} (Confirmed)"

        return f"{report_name} - {date_str}"

    def _get_report_data(self):
        self.ensure_one()
        all_report_data = []

        if self.filter_by == "salesperson":
            salespersons = self.salesperson_ids

            if not salespersons and self.sale_region_id:
                domain = [("sale_team_id", "!=", False), ("share", "=", False)]
                if self.sale_region_id:
                    domain += [
                        ("partner_id.salesregion_id", "=", self.sale_region_id.id)
                    ]
                salespersons = self.env["res.users"].search(domain)

            for salesperson in salespersons:
                report_data = self._prepare_single_salesperson_data(salesperson)
                all_report_data.append(report_data)

        elif self.filter_by == "product":
            products = self.product_ids

            if not products and self.product_category_id:
                domain = [
                    ("categ_id", "child_of", self.product_category_id.id),
                    ("sale_ok", "=", True),
                ]
                products = self.env["product.product"].search(domain)

            for product in products:
                report_data = self._prepare_single_product_data(product)
                all_report_data.append(report_data)

        elif self.filter_by == "customer":
            partners = self.partner_ids

            if not partners and self.sale_region_id:
                domain = [
                    ("state", "=", "sale"),
                ]
                domain += self._get_date_order_domain()
                domain += self._get_region_domain()

                so_ids = self.env["sale.order"].search(domain)
                partners = so_ids.mapped("partner_id")

            for partner in partners:
                report_data = self._prepare_single_customer_data(partner)
                all_report_data.append(report_data)

        elif self.filter_by == "market_region":
            report_data = self._prepare_single_market_region_data()
            all_report_data.append(report_data)

        elif self.filter_by == "top_ten":
            report_data = self._prepare_top_ten_data()
            all_report_data.append(report_data)

        return all_report_data

    def action_jasper(self):
        self.ensure_one()

        if self.is_commission_confirmed and self.filter_by == "salesperson":
            TimestampModel = self.env["sale.commission.timestamp"]
            logs_to_create = []

            for line in self.line_ids:
                if line.amount_commission > 0:
                    logs_to_create.append(
                        {
                            "salesperson_id": line.salesperson_id.id,
                            "sale_order_name": line.sale_order_name,
                            "invoice_names": line.invoice_name,
                            "commission_amount": line.amount_commission,
                        }
                    )

            if logs_to_create:
                TimestampModel.create(logs_to_create)

        filter_by = str(self.filter_by) if self.filter_by else None

        sale_region_id = str(self.sale_region_id.id) if self.sale_region_id else None
        salesperson_ids = (
            ",".join(map(str, self.salesperson_ids.ids))
            if self.salesperson_ids
            else None
        )
        partner_ids = (
            ",".join(map(str, self.partner_ids.ids)) if self.partner_ids else None
        )

        product_category_id = (
            str(self.product_category_id.id) if self.product_category_id else None
        )
        product_ids = (
            ",".join(map(str, self.product_ids.ids)) if self.product_ids else None
        )

        is_commission_confirmed = 1 if self.is_commission_confirmed else None
        date_from = self.date_from.strftime("%Y-%m-%d") if self.date_from else None
        date_to = self.date_to.strftime("%Y-%m-%d") if self.date_to else None
        wizard_id = str(self.id) if self.id else None
        state_id = ",".join(map(str, self.state_id.ids)) if self.state_id else None

        data = {
            "filter_by": filter_by,
            "sale_region_id": sale_region_id,
            "salesperson_ids": salesperson_ids,
            "partner_ids": partner_ids,
            "product_category_id": product_category_id,
            "product_ids": product_ids,
            "is_commission_confirmed": is_commission_confirmed,
            "date_from": date_from,
            "date_to": date_to,
            "wizard_id": wizard_id,
            "state_id": state_id,
        }

        if not self.report_id:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "การตั้งค่าไม่ถูกต้อง",
                    "message": "  • ไม่พบรายงาน Jasper Report กรุณาตรวจสอบการตั้งค่า",
                    "type": "danger",
                    "sticky": False,
                },
            }

        return self.report_id.run_report(docids=[self.ids[0]], data=data)

    def action_compute_lines(self):
        self.ensure_one()
        if self.date_from and self.date_to and self.date_from > self.date_to:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "วันที่ไม่ถูกต้อง",
                    "message": "  • วันที่เริ่มต้น ต้องมาก่อน หรือวันเดียวกับ วันที่สิ้นสุด",
                    "type": "danger",
                    "sticky": False,
                },
            }

        self.line_ids.unlink()

        if not self.filter_by:
            return

        all_data = self._get_report_data()
        lines = []

        if self.filter_by == "salesperson":
            for data_group in all_data:
                fallback_sp_id = data_group.get("salesperson_id")

                for item in data_group.get("sale_orders", []):
                    lines.append(
                        {
                            "wizard_id": self.id,
                            "salesperson_id": item.get("salesperson_id")
                            or fallback_sp_id,
                            "sale_order_name": item.get("sale_order_name"),
                            "customer_name": item.get("customer_name"),
                            "invoice_name": item.get("invoice_name"),
                            "credit_note_name": item.get("credit_note_name"),
                            "amount_sale_total": item.get("amount_sale_total", 0.0),
                            "amount_invoice_total": item.get(
                                "amount_invoice_total", 0.0
                            ),
                            "amount_payment_total": item.get(
                                "amount_payment_total", 0.0
                            ),
                            "amount_credit_note_total": item.get(
                                "amount_credit_note_total", 0.0
                            ),
                            "amount_commission": item.get(
                                "amount_commission_total", 0.0
                            ),
                        }
                    )

        elif self.filter_by == "market_region":
            for data_group in all_data:
                for item in data_group.get("market_region_data", []):
                    lines.append(
                        {
                            "wizard_id": self.id,
                            "salesperson_id": item.get("salesperson_id"),
                            "sale_order_name": item.get("sale_order_name"),
                            "customer_name": item.get("customer_name"),
                            "product_name": item.get("product_name"),
                            "product_uom_qty": item.get("quantity", 0.0),
                            "currency_name": item.get("currency_name"),
                            "exchange_rate": item.get("exchange_rate", 1.0),
                            "amount_foreign": item.get("amount_foreign", 0.0),
                            "amount_thb": item.get("amount_thb", 0.0),
                        }
                    )

        elif self.filter_by == "product":
            for data_group in all_data:
                prod_cat_name = data_group.get("product_category_name")
                prod_name = data_group.get("product_name")

                for item in data_group.get("product_sales_data", []):
                    lines.append(
                        {
                            "wizard_id": self.id,
                            "salesperson_id": item.get("salesperson_id"),
                            "sale_order_name": item.get("sale_order_name"),
                            "customer_name": item.get("customer_name"),
                            "product_uom_qty": item.get("quantity", 0.0),
                            "amount_sale_total": item.get("amount_untaxed", 0.0),
                            "product_name": prod_name,
                            "product_category_name": prod_cat_name,
                        }
                    )

        elif self.filter_by == "customer":
            for data_group in all_data:
                cust_name = data_group.get("customer_name")
                for item in data_group.get("customer_sales_data", []):
                    lines.append(
                        {
                            "wizard_id": self.id,
                            "customer_name": cust_name,
                            "sale_order_name": item.get("sale_order_name"),
                            "salesperson_id": self.env["res.users"]
                            .search(
                                [("name", "=", item.get("salesperson_name"))], limit=1
                            )
                            .id,
                            "invoice_name": item.get("invoice_name"),
                            "credit_note_name": item.get("credit_note_name"),
                            "amount_sale_total": item.get("amount_sale_total", 0.0),
                            "amount_invoice_total": item.get(
                                "amount_invoice_total", 0.0
                            ),
                            "amount_credit_note_total": item.get(
                                "amount_credit_note_total", 0.0
                            ),
                            "amount_payment_total": item.get(
                                "amount_payment_total", 0.0
                            ),
                        }
                    )

        elif self.filter_by == "top_ten":
            if all_data:
                data = all_data[0]
                for item in data.get("top_qty", []):
                    lines.append(
                        {
                            "wizard_id": self.id,
                            "rank_type": "qty",
                            "product_name": item.get("product_name"),
                            "product_uom_qty": item.get("quantity", 0.0),
                            "amount_sale_total": item.get("amount", 0.0),
                        }
                    )
                for item in data.get("top_amount", []):
                    lines.append(
                        {
                            "wizard_id": self.id,
                            "rank_type": "amount",
                            "product_name": item.get("product_name"),
                            "product_uom_qty": item.get("quantity", 0.0),
                            "amount_sale_total": item.get("amount", 0.0),
                        }
                    )

        if lines:
            self.env["sale.analysis.report.line"].create(lines)

        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_export_excel(self):
        self.ensure_one()

        if self.is_commission_confirmed and self.filter_by == "salesperson":
            TimestampModel = self.env["sale.commission.timestamp"]
            logs_to_create = []

            for line in self.line_ids:
                if line.amount_commission > 0:
                    logs_to_create.append(
                        {
                            "salesperson_id": line.salesperson_id.id,
                            "sale_order_name": line.sale_order_name,
                            "invoice_names": line.invoice_name,
                            "commission_amount": line.amount_commission,
                        }
                    )

            if logs_to_create:
                TimestampModel.create(logs_to_create)

        report_xml_id = False
        if self.filter_by == "salesperson":
            report_xml_id = "sale_analysis_report.action_sale_analysis_saleman_xlsx"
        elif self.filter_by == "product":
            report_xml_id = "sale_analysis_report.action_sale_analysis_product_xlsx"
        elif self.filter_by == "customer":
            report_xml_id = "sale_analysis_report.action_sale_analysis_customer_xlsx"
        elif self.filter_by == "market_region":
            report_xml_id = (
                "sale_analysis_report.action_sale_analysis_market_region_xlsx"
            )
        elif self.filter_by == "top_ten":
            report_xml_id = "sale_analysis_report.action_sale_analysis_top_ten_xlsx"

        if not report_xml_id:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "การตั้งค่าไม่ถูกต้อง",
                    "message": "  • ไม่มีรายงานที่ถูกต้อง โปรดตรวจสอบการตั้งค่า",
                    "type": "danger",
                    "sticky": False,
                },
            }

        return self.env.ref(report_xml_id).report_action(self)
