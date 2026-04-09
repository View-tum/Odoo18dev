# -*- coding: utf-8 -*-

from odoo import api, models


class MrpProductionSchedule(models.Model):
    """
    ใช้ BOM ที่เลือกบน MPS (field bom_id เดิมของ Odoo)
    ตอนสร้าง MO จาก MPS
    """
    _inherit = "mrp.production.schedule"

    def _prepare_mo_vals(self):
        """
        ฟังก์ชันนี้ถูกใช้ตอน MPS สร้าง mrp.production
        เรา override เพื่อ force ให้ใช้ bom_id จาก schedule
        """
        self.ensure_one()
        vals = super()._prepare_mo_vals()

        if self.bom_id:
            # ใช้ BOM ที่เลือกใน MPS
            vals["bom_id"] = self.bom_id.id
            # ถ้า BOM มี routing field อยู่ในโมเดลและมีค่า routing ให้ใช้ routing ของ BOM
            if "routing_id" in self.bom_id._fields and getattr(self.bom_id, "routing_id", False) and not vals.get("routing_id"):
                vals["routing_id"] = self.bom_id.routing_id.id

        return vals

    def _get_procurement_extra_values(self, forecast_values):
        """Inject mps_schedule_id so stock.rule can pick it up."""
        values = super()._get_procurement_extra_values(forecast_values)
        values["mps_schedule_id"] = self.id
        return values

    def get_procurement_values(self, forecast_values):
        """Ensure mps_schedule_id is passed in get_procurement_values as well."""
        res = super().get_procurement_values(forecast_values)
        if isinstance(res, list):
            for vals in res:
                vals["mps_schedule_id"] = self.id
        elif isinstance(res, dict):
            res["mps_schedule_id"] = self.id
        return res


class MrpProduction(models.Model):
    """
    Backup อีกชั้น: ถ้า create MO พร้อม bom_id
    ให้ routing_id ตาม BOM เสมอถ้ายังไม่ได้ set
    """
    _inherit = "mrp.production"

    @api.model_create_multi
    def create(self, vals_list):
        Bom = self.env["mrp.bom"]
        for vals in vals_list:
            bom_id = vals.get("bom_id")
            if not bom_id:
                continue

            bom = Bom.browse(bom_id)
            if not bom.exists():
                continue

            # ถ้า BOM มีฟิลด์ routing_id อยู่ในโมเดลและ BOM มี routing ให้ตั้ง routing_id ให้ MO
            if "routing_id" in bom._fields and getattr(bom, "routing_id", False) and not vals.get("routing_id"):
                vals["routing_id"] = bom.routing_id.id

        return super().create(vals_list)


class StockRule(models.Model):
    _inherit = "stock.rule"

    def _prepare_mo_vals(
        self,
        product_id,
        product_qty,
        product_uom,
        location_dest_id,
        name,
        origin,
        company_id,
        values,
        bom,
    ):
        vals = super()._prepare_mo_vals(
            product_id,
            product_qty,
            product_uom,
            location_dest_id,
            name,
            origin,
            company_id,
            values,
            bom,
        )
        schedule_id = values.get("mps_schedule_id")
        if schedule_id:
            schedule = (
                self.env["mrp.production.schedule"]
                .sudo()
                .browse(schedule_id)
            )
            if schedule and schedule.bom_id:
                vals["bom_id"] = schedule.bom_id.id
                if (
                    "routing_id" in schedule.bom_id._fields
                    and schedule.bom_id.routing_id
                    and not vals.get("routing_id")
                ):
                    vals["routing_id"] = schedule.bom_id.routing_id.id
        return vals
