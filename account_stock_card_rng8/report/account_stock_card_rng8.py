# -*- coding: utf-8 -*-
from odoo import models, fields, _
import base64
from datetime import datetime, time
import pytz

from .account_stock_card_rng8_excel import AccountStockCardRng8ExcelWriter


class AccountStockCardRNG8(models.TransientModel):
    _name = "account.stock.card.rng8"
    _description = "Account Stock Card RNG8 Report"

    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda s: s.env.company,
        required=True,
        help="(365 custom) บริษัทที่ต้องการออกรายงาน",
    )
    product_category_id = fields.Many2one(
        comodel_name="product.category",
        string="Product Category",
        domain="[('parent_id','=', 1)]",
        required=True,
        help="(365 custom) หมวดหมู่สินค้าที่ต้องการตรวจสอบสต็อก",
    )
    location_id = fields.Many2one(
        comodel_name="stock.location",
        domain="[('usage','=','internal'), ('company_id','in',[False, company_id])]",
        string="Location",
        required=True,
        help="(365 custom) คลังสินค้าที่ต้องการดึงข้อมูล",
    )
    include_child_locations = fields.Boolean(
        default=True,
        string="Include Sub-Locations",
        help="(365 custom) หากเลือกจะรวมคลังสินค้าย่อยภายใต้คลังที่เลือกด้วย",
    )
    date_from = fields.Date(
        string="Date From",
        required=True,
        default=lambda self: fields.Date.to_date(datetime.now().replace(day=1)),
        help="(365 custom) วันที่เริ่มต้นของช่วงเวลาที่ต้องการดูรายงาน",
    )
    date_to = fields.Date(
        string="Date To",
        required=True,
        default=fields.Date.context_today,
        help="(365 custom) วันที่สิ้นสุดของช่วงเวลาที่ต้องการดูรายงาน",
    )

    def _get_location_ids(self):
        """
        TH: ดึง ID ของคลังสินค้าที่เลือก รวมถึงคลังย่อยหากมีการตั้งค่าให้รวม
        EN: Retrieve the selected location IDs, including child locations if configured to include them.
        """
        if self.include_child_locations and self.location_id:
            return (
                self.env["stock.location"]
                .search(
                    [
                        ("id", "child_of", self.location_id.id),
                        ("usage", "=", "internal"),
                    ]
                )
                .ids
            )
        return [self.location_id.id]

    def _compute_period_data(self, product, location_ids, date_from_utc, date_to_utc):
        """
        TH: คำนวณข้อมูลการเคลื่อนไหวของสินค้า (ยอดยกมา, รับเข้า, จ่ายออก, คงเหลือ) ตามช่วงเวลาและคลังสินค้าที่กำหนด
        EN: Compute product movement data (opening, incoming, outgoing, ending) based on the specified period and locations.
        """
        domain = [
            ("state", "=", "done"),
            ("product_id", "=", product.id),
            ("company_id", "=", self.company_id.id),
            ("date", "<=", date_to_utc),
            "|",
            ("location_id", "in", location_ids),
            ("location_dest_id", "in", location_ids),
        ]

        move_lines = self.env["stock.move.line"].search(domain)
        product_uom = product.uom_id

        data = {
            "open_qty": 0.0,
            "open_val": 0.0,
            "in_qty": 0.0,
            "in_val": 0.0,
            "out_qty": 0.0,
            "out_val": 0.0,
            "end_qty": 0.0,
            "end_val": 0.0,
        }

        for line in move_lines:
            qty = line.quantity if "quantity" in line else line.qty_done
            if line.product_uom_id and line.product_uom_id != product_uom:
                qty = line.product_uom_id._compute_quantity(qty, product_uom)

            unit_cost = 0.0
            layers = line.move_id.stock_valuation_layer_ids
            if layers:
                val_sum = sum(layers.mapped("value"))
                qty_sum = sum(layers.mapped("quantity"))
                if qty_sum:
                    unit_cost = abs(val_sum / qty_sum)

            if unit_cost == 0.0:
                unit_cost = line.move_id.price_unit or product.standard_price

            is_in = (line.location_dest_id.id in location_ids) and (
                line.location_id.id not in location_ids
            )
            is_out = (line.location_id.id in location_ids) and (
                line.location_dest_id.id not in location_ids
            )

            val_total = qty * unit_cost

            if line.date < date_from_utc:
                if is_in:
                    data["open_qty"] += qty
                    data["open_val"] += val_total
                elif is_out:
                    data["open_qty"] -= qty
                    data["open_val"] -= val_total
            else:
                if is_in:
                    data["in_qty"] += qty
                    data["in_val"] += val_total
                elif is_out:
                    data["out_qty"] += qty
                    data["out_val"] += val_total

        data["end_qty"] = data["open_qty"] + data["in_qty"] - data["out_qty"]
        data["end_val"] = data["open_val"] + data["in_val"] - data["out_val"]

        return data

    def _prepare_report_data(self):
        """
        TH: เตรียมข้อมูลสำหรับรายงาน โดยค้นหาสินค้าและรวบรวมข้อมูลการเคลื่อนไหวเพื่อส่งต่อไปยัง Excel Writer
        EN: Prepare report data by searching for products and aggregating movement data to pass to the Excel Writer.
        """
        child_ids = self.product_category_id.child_id.ids + [
            self.product_category_id.id
        ]
        products = self.env["product.product"].search(
            [
                ("product_tmpl_id.categ_id", "in", child_ids),
                ("product_tmpl_id.type", "=", "consu"),
            ]
        )

        if not products:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "แจ้งเตือน",
                    "message": "  • ไม่พบ สินค้าที่ตรงกับเงื่อนไขที่กำหนด",
                    "type": "warning",
                    "sticky": False,
                },
            }

        user_tz = pytz.timezone(self.env.user.tz or "UTC")

        dt_from_combine = datetime.combine(self.date_from, time.min)
        local_dt_from = user_tz.localize(dt_from_combine)
        date_from_utc = local_dt_from.astimezone(pytz.UTC).replace(tzinfo=None)

        dt_to_combine = datetime.combine(self.date_to, time.max)
        local_dt_to = user_tz.localize(dt_to_combine)
        date_to_utc = local_dt_to.astimezone(pytz.UTC).replace(tzinfo=None)

        location_ids = self._get_location_ids()

        lines = []
        for product in products:
            res = self._compute_period_data(
                product, location_ids, date_from_utc, date_to_utc
            )

            if (
                abs(res["open_qty"]) < 0.001
                and abs(res["in_qty"]) < 0.001
                and abs(res["out_qty"]) < 0.001
                and abs(res["end_qty"]) < 0.001
            ):
                continue

            open_cost = (res["open_val"] / res["open_qty"]) if res["open_qty"] else 0.0
            in_cost = (res["in_val"] / res["in_qty"]) if res["in_qty"] else 0.0
            out_cost = (res["out_val"] / res["out_qty"]) if res["out_qty"] else 0.0
            end_cost = (res["end_val"] / res["end_qty"]) if res["end_qty"] else 0.0

            lines.append(
                {
                    "code": product.default_code,
                    "name": product.name,
                    "uom": product.uom_id.name,
                    "category": product.categ_id.name,
                    "open_qty": res["open_qty"],
                    "open_cost": open_cost,
                    "open_val": res["open_val"],
                    "in_qty": res["in_qty"],
                    "in_cost": in_cost,
                    "in_val": res["in_val"],
                    "out_qty": res["out_qty"],
                    "out_cost": out_cost,
                    "out_val": res["out_val"],
                    "end_qty": res["end_qty"],
                    "end_cost": end_cost,
                    "end_val": res["end_val"],
                }
            )

        metadata = {
            "date_from": self.date_from,
            "date_to": self.date_to,
            "category": self.product_category_id.display_name,
            "location": self.location_id.display_name,
        }

        return metadata, lines

    def action_export_xlsx(self):
        """
        TH: การทำงานหลักเพื่อเรียกการเตรียมข้อมูล สร้างไฟล์ Excel และส่งคืน Action สำหรับดาวน์โหลดไฟล์
        EN: Main action to trigger data preparation, generate the Excel file, and return the download action.
        """
        self.ensure_one()
        metadata, lines = self._prepare_report_data()

        writer = AccountStockCardRng8ExcelWriter()
        xlsx_content = writer.generate(metadata, lines)

        out_data = base64.b64encode(xlsx_content)
        filename = f"Stock_Card_{self.date_to}.xlsx"

        attachment = self.env["ir.attachment"].create(
            {
                "name": filename,
                "type": "binary",
                "datas": out_data,
                "res_model": self._name,
                "public": False,
            }
        )

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "self",
        }
