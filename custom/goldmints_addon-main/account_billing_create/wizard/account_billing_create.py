# -*- coding: utf-8 -*-
from odoo import models, fields, api, Command
from dateutil.relativedelta import relativedelta


class AccountBillingCreate(models.TransientModel):
    _name = "account.billing.create"
    _description = "Mass Create Billing Wizard"

    # --- Filter Section ---
    route_id = fields.Many2one(
        comodel_name="delivery.route",
        string="สาย",
        help="(365 custom) เลือกสายการส่งเพื่อกรองลูกค้าในเขตที่เกี่ยวข้อง",
    )
    subregion_ids = fields.Many2many(
        comodel_name="delivery.sub.region",
        domain="[('route_id', '=', route_id)]",
        string="เขต",
        help="(365 custom) เลือกเขตการส่งเพื่อกรองลูกค้าในเขตที่เกี่ยวข้อง",
    )
    team_id = fields.Many2one(
        comodel_name="crm.team",
        string="ทีมขาย",
        help="(365 custom) เลือกทีมขายเพื่อกรองรายชื่อพนักงาน",
    )
    salesperson_id = fields.Many2one(
        comodel_name="res.users",
        string="พนักงานขาย",
        domain="[('sale_team_id', '=', team_id), ('share', '=', False)] if team_id else []",
        help="(365 custom) เลือกพนักงานขายเพื่อกรองลูกค้าในความดูแลของพนักงานขายนั้น",
    )
    customer_ids = fields.Many2many(
        comodel_name="res.partner",
        string="ลูกค้า/ผู้ขาย",
        domain="['|', ('customer_rank', '>', 0), ('supplier_rank', '>', 0)]",
        help="(365 custom) ระบุลูกค้าหรือผู้ขายเพื่อกรองข้อมูล",
    )

    billing_mode = fields.Selection(
        selection=[
            ("out_invoice", "Customer Invoice (ลูกหนี้)"),
            ("in_invoice", "Vendor Bill (เจ้าหนี้)"),
            ("netting", "Netting (หักกลบหนี้)"),
        ],
        string="ประเภทการเรียกเก็บเงิน",
        default="out_invoice",
        required=True,
        help="(365 custom) เลือกประเภทของการเรียกเก็บเงินที่ต้องการสร้าง",
    )
    threshold_date_type = fields.Selection(
        selection=[
            ("invoice_date", "Invoice Date (วันที่ใบแจ้งหนี้)"),
            ("invoice_date_due", "Due Date (วันครบกำหนด)"),
        ],
        string="ประเภทวันที่เกณฑ์",
        default="invoice_date_due",
        help="(365 custom) เลือกประเภทวันที่เกณฑ์เพื่อใช้ในการกรองใบแจ้งหนี้/บิล",
    )

    def _get_year_selection(self):
        """
        TH: (Internal) สร้างรายการตัวเลือกปี (ปีปัจจุบัน +/- 5 ปี) สำหรับให้ผู้ใช้เลือกในฟอร์ม
        EN: (Internal) Generates a list of years (Current Year +/- 5) for user selection in the form.
        """
        current_year = fields.Date.today().year
        return [(str(y), str(y)) for y in range(current_year - 5, current_year + 5)]

    select_year = fields.Selection(
        selection=_get_year_selection,
        string="Select Year",
        default=lambda self: str(fields.Date.today().year),
        help="(365 custom) Select year to auto-fill the date range.",
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
        help="(365 custom) เลือกเดือนเพื่อกรอกช่วงวันที่โดยอัตโนมัติ",
    )
    date_from = fields.Date(
        string="วันที่เริ่มต้น",
        help="(365 custom) วันที่เริ่มต้นของช่วงวางบิลของลูกค้า",
    )
    date_to = fields.Date(
        string="วันที่สิ้นสุด",
        help="(365 custom) วันที่สิ้นสุดของช่วงวางบิลของลูกค้า",
    )

    @api.model
    def default_get(self, fields_list):
        """
        TH: (Override) กำหนดค่าเริ่มต้นให้กับฟิลด์ต่างๆ เช่น วันที่เริ่มต้น/สิ้นสุด และเทมเพลตรายงาน เมื่อเปิด Create
        EN: (Override) Initializes default values for fields such as Start/End Date and Report Template when the Create is opened.
        """
        res = super(AccountBillingCreate, self).default_get(fields_list)

        if "date_to" in fields_list and not res.get("date_to"):
            res["date_to"] = fields.Date.context_today(self)

        if "date_from" in fields_list and not res.get("date_from"):
            res["date_from"] = fields.Date.context_today(self)

        return res

    @api.onchange("route_id")
    def _onchange_route_id(self):
        """
        TH: (Onchange) ล้างค่ารายการลูกค้าเมื่อมีการเปลี่ยนพนักงานขาย
        EN: (Onchange) Clears the customer list when the route is changed.
        """
        self.salesperson_id = False
        self.customer_ids = [Command.clear()]
        self.subregion_ids = [Command.clear()]

    @api.onchange("team_id")
    def _onchange_team_id(self):
        """
        TH: (Onchange) ล้างค่ารายการลูกค้าเมื่อมีการเปลี่ยนทีมขาย
        EN: (Onchange) Clears the customer list when the sales team is changed.
        """
        self.route_id = False
        self.customer_ids = [Command.clear()]

        # if not self.team_id:
        self.salesperson_id = False

    @api.onchange("customer_ids")
    def _onchange_customer_ids(self):
        """
        TH: (Onchange) ล้างค่าพนักงานขายเมื่อมีการระบุลูกค้าเจาะจง
        EN: (Onchange) Clears the salesperson field when specific customers are selected.
        """
        if self.customer_ids:
            self.salesperson_id = False

    @api.onchange("select_month", "select_year")
    def _onchange_period(self):
        """
        TH: (Onchange) คำนวณวันที่เริ่มต้นและสิ้นสุดโดยอัตโนมัติตามเดือนและปีที่ผู้ใช้เลือก
        EN: (Onchange) Automatically calculates the Start Date and End Date based on the selected month and year.
        """
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

    def _show_warning(self, title, message):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": message,
                "type": "warning",
                "sticky": False,
            },
        }

    def action_create_billing(self):
        """
        ค้นหา Invoice ตามเงื่อนไข และสร้าง Billing แยกตามลูกค้า
        [Optimized] ใช้ SQL และ Database Search แทนการวนลูป Python เพื่อความรวดเร็ว
        """
        if not self.route_id and not self.salesperson_id and not self.customer_ids.ids:
            return self._show_warning(
                "การตั้งค่าไม่ถูกต้อง",
                "  • โปรดระบุ สาย, พนักงานขาย หรือ ลูกค้า อย่างน้อยหนึ่งตัวกรอง",
            )

        if self.date_from and self.date_to and self.date_from > self.date_to:
            return self._show_warning(
                "วันที่ไม่ถูกต้อง", "  • วันที่เริ่มต้น ต้องมาก่อน หรือวันเดียวกับ วันที่สิ้นสุด"
            )

        query_billed = """
            SELECT DISTINCT abl.move_id
            FROM account_billing_line AS abl
            JOIN account_billing AS ab ON abl.billing_id = ab.id
            WHERE ab.state = 'billed'
        """
        self.env.cr.execute(query_billed)
        billed_move_ids = [row[0] for row in self.env.cr.fetchall()]

        target_types = []
        if self.billing_mode == "netting":
            target_types = ["out_invoice", "out_refund", "in_invoice", "in_refund"]
        elif self.billing_mode == "in_invoice":
            target_types = ["in_invoice", "in_refund"]
        else:
            target_types = ["out_invoice", "out_refund"]

        domain = [
            ("move_type", "in", target_types),
            ("state", "=", "posted"),
            ("payment_state", "in", ["not_paid", "partial"]),
            (self.threshold_date_type, "<", self.date_to),
            ("id", "not in", billed_move_ids),
        ]

        if self.salesperson_id:
            customers = self.env["res.partner"].search(
                [("user_id", "=", self.salesperson_id.id)]
            )

            if not customers:
                return self._show_warning("ไม่พบลูกค้า", "ไม่พบลูกค้าในพื้นที่การส่งที่เลือก")
            else:
                domain.append(("partner_id", "in", customers.ids))
        elif self.customer_ids:
            domain.append(("partner_id", "in", self.customer_ids.ids))
        elif self.subregion_ids:
            customers = self.env["res.partner"].search(
                [("subregion_id", "in", self.subregion_ids.ids)]
            )
            if not customers:
                return self._show_warning("ไม่พบลูกค้า", "ไม่พบลูกค้าในพื้นที่การส่งที่เลือก")
            else:
                domain.append(("partner_id", "in", customers.ids))

        groups = self.env["account.move"]._read_group(
            domain=domain + [("partner_id", "!=", False)],
            groupby=["partner_id"],
        )
        all_partner_ids = [partner[0].id for partner in groups]

        if not all_partner_ids:
            return self._show_warning(
                "แจ้งเตือน", "  • ไม่พบ Invoice หรือ Bills ที่ตรงกับเงื่อนไขการค้นหา"
            )

        pps_model = self.env["pps.schedule"]
        schedules_any = pps_model.search(
            [
                ("partner_id", "in", all_partner_ids),
                ("schedule_type", "=", "billing"),
                ("active", "=", True),
            ]
        )
        partner_ids_with_schedule = set(schedules_any.mapped("partner_id.id"))
        dt_from = fields.Datetime.to_datetime(self.date_from)
        dt_to = fields.Datetime.to_datetime(self.date_to) + relativedelta(
            days=1, seconds=-1
        )

        schedules_in_range = pps_model.search(
            [
                ("partner_id", "in", all_partner_ids),
                ("schedule_type", "=", "billing"),
                ("active", "=", True),
                ("next_run", ">=", dt_from),
                ("next_run", "<=", dt_to),
            ]
        )
        partner_ids_in_range = set(schedules_in_range.mapped("partner_id.id"))
        partner_ids_no_schedule = set(all_partner_ids) - partner_ids_with_schedule
        final_partner_ids = list(partner_ids_no_schedule | partner_ids_in_range)

        if not final_partner_ids:
            return self._show_warning(
                "แจ้งเตือน", "  • พบ Invoice แต่ไม่มีลูกค้าที่ถึงรอบวางบิลในช่วงวันที่กำหนด"
            )

        created_billings = self.env["account.billing"]
        partners = self.env["res.partner"].browse(final_partner_ids)
        bill_type_value = (
            "in_invoice" if self.billing_mode == "in_invoice" else "out_invoice"
        )

        for partner in partners:
            partner_currency_id = (
                partner.property_product_pricelist.currency_id.id
                or self.env.company.currency_id.id
            )

            billing = self.env["account.billing"].create(
                {
                    "partner_id": partner.id,
                    "bill_type": bill_type_value,
                    "billing_mode": self.billing_mode,
                    "date": fields.Date.context_today(self),
                    "start_date": self.date_from,
                    "threshold_date": self.date_to,
                    "threshold_date_type": self.threshold_date_type,
                    "company_id": self.env.company.id,
                    "currency_id": partner_currency_id,
                }
            )

            billing.compute_lines()

            if billing.billing_line_ids:
                created_billings += billing
            else:
                billing.unlink()

        if not created_billings:
            return self._show_warning(
                "แจ้งเตือน",
                "  • สร้างเอกสารเรียกเก็บเงินแล้ว แต่ไม่พบรายการใดๆ (อาจเกิดจากความไม่ตรงกันของสกุลเงินหรือตัวกรองอื่นๆ)",
            )

        return {
            "name": ("Generated Billings"),
            "type": "ir.actions.act_window",
            "res_model": "account.billing",
            "view_mode": "list,form",
            "domain": [("id", "in", created_billings.ids)],
        }
