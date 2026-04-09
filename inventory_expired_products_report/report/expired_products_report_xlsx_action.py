# -*- coding: utf-8 -*-
from odoo import models
from datetime import date, datetime, timedelta
import io
import base64
import xlsxwriter


class ExpiredProductsReportXlsxWizard(models.TransientModel):
    """
    ต่อเติม wizard เดิม (expired.products.report) ให้มี:
    - ฟังก์ชัน query สำหรับ XLSX (_get_xlsx_lines)
    - ฟังก์ชันตั้งชื่อไฟล์ (_get_xlsx_filename)
    - ปุ่ม action_export_xlsx สำหรับสร้าง Excel
    """
    _inherit = "expired.products.report"

    # ------------------------------------------------------------------
    # QUERY สำหรับ XLSX
    # ------------------------------------------------------------------
    def _get_xlsx_lines(self):
        """
        ดึงข้อมูลสินค้า (ตาม filter):
        - product_category_id
        - product_ids
        - select_year / select_month
        - date_from / date_to

        โครง JOIN ตาม Jasper:
        product_product, product_template, stock_quant, stock_location,
        stock_lot, product_category
        (เพิ่มเติม: join uom_uom เพื่อเอาชื่อ UoM มาแสดงใน Excel)
        """
        self.ensure_one()

        query = """
            SELECT
                sq.expiration_date,
                pp.create_date     AS create_date,
                pp.id              AS product_id,
                pp.default_code    AS product_code,
                COALESCE(
                    pt.name->>'th_TH',
                    pt.name->>'en_US'
                )                  AS product_name,
                sq.quantity,
                COALESCE(
                    uom.name->>'en_US',
                    uom.name->>'th_TH'
                )                  AS uom_name,
                sl.complete_name   AS location_name,
                slot.name          AS lot_name,
                slot.manufacturing_date AS manufacturing_date,
                pc.complete_name   AS category_name
            FROM stock_quant sq
            JOIN product_product pp   ON pp.id = sq.product_id
            JOIN product_template pt  ON pt.id = pp.product_tmpl_id
            LEFT JOIN product_category pc ON pc.id = pt.categ_id
            LEFT JOIN stock_location  sl  ON sl.id = sq.location_id
            LEFT JOIN uom_uom         uom ON uom.id = pt.uom_id
            LEFT JOIN stock_lot       slot ON slot.id = sq.lot_id
            WHERE sl.usage = 'internal'
              AND sq.quantity > 0
        """

        params = []

        # ถ้าเลือก category → filter pc.id
        if self.product_category_id:
            query += " AND pc.id = %s"
            params.append(self.product_category_id.id)

        # ถ้าเลือก products → filter pp.id
        if self.product_ids:
            query += " AND pp.id IN %s"
            params.append(tuple(self.product_ids.ids))

        # date_from + date_to
        if self.date_from and self.date_to:
            query += """
                AND sq.expiration_date >= %s::date
                AND sq.expiration_date <  (%s::date + INTERVAL '1 day')
            """
            params.extend([self.date_from, self.date_to])

        # year
        if self.select_year:
            year_int = int(self.select_year)
            query += " AND EXTRACT(YEAR FROM sq.expiration_date) = %s"
            params.append(year_int)

        # month
        if self.select_month:
            month_int = int(self.select_month)
            query += " AND EXTRACT(MONTH FROM sq.expiration_date) = %s"
            params.append(month_int)

        query += " ORDER BY sq.expiration_date, pp.id, slot.name"

        self.env.cr.execute(query, params)
        cols = [c[0] for c in self.env.cr.description]
        return [dict(zip(cols, row)) for row in self.env.cr.fetchall()]

    # ------------------------------------------------------------------
    # ตั้งชื่อไฟล์ XLSX
    # ------------------------------------------------------------------
    def _get_xlsx_filename(self):
        """คืนชื่อไฟล์ XLSX ตาม filter ที่เลือกใน wizard"""
        self.ensure_one()

        parts = ["Expired_Products"]

        # ถ้ามีช่วงวันที่ ให้ใส่ต่อท้าย
        if self.date_from and self.date_to:
            parts.append(
                "%s_to_%s"
                % (
                    self.date_from.strftime("%Y%m%d"),
                    self.date_to.strftime("%Y%m%d"),
                )
            )
        # ถ้าเลือกปี / เดือน
        elif self.select_year:
            p = str(self.select_year)
            if self.select_month:
                try:
                    p += "-%02d" % int(self.select_month)
                except Exception:
                    p += "-%s" % self.select_month
            parts.append(p)

        filename = "_".join(parts) + ".xlsx"
        return filename

    # ------------------------------------------------------------------
    # ปุ่ม Export XLSX (สร้างไฟล์ + attachment + act_url)
    # ------------------------------------------------------------------
    def action_export_xlsx(self):
        self.ensure_one()

        # 1) เตรียม buffer + workbook
        bio = io.BytesIO()
        workbook = xlsxwriter.Workbook(bio, {"in_memory": True})

        # 2) ใช้ generate_xlsx_report จาก AbstractModel XLSX
        report_model = self.env[
            "report.inventory_expired_products_report.expired_products_xlsx"
        ]
        report_model.generate_xlsx_report(
            workbook,
            {"wizard_id": self.id},
            self,
        )

        # 3) ปิด workbook แล้วดึง binary
        workbook.close()
        xlsx_data = bio.getvalue()
        bio.close()

        # 4) ตั้งชื่อไฟล์จาก helper
        filename = self._get_xlsx_filename()

        # 5) สร้าง attachment แล้วคืน act_url ให้ browser ดาวน์โหลด
        attachment = self.env["ir.attachment"].create({
            "name": filename,
            "type": "binary",
            "datas": base64.b64encode(xlsx_data),
            "res_model": self._name,
            "res_id": self.id,
            "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "public": False,
        })

        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=true" % attachment.id,
            "target": "self",
        }
