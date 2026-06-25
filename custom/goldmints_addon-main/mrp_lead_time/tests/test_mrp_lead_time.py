from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "mrp_lead_time")
class TestMrpLeadTime(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.uom = cls.env.ref("uom.product_uom_unit")
        cls.warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.env.company.id)], limit=1)
        cls.product = cls.env["product.product"].create(
            {
                "name": "Lead Time Finished Product",
                "type": "consu",
                "mfg_lead_time": 5,
            }
        )
        cls.bom = cls.env["mrp.bom"].create(
            {
                "product_tmpl_id": cls.product.product_tmpl_id.id,
                "product_qty": 1.0,
                "product_uom_id": cls.uom.id,
            }
        )
        cls.rule = cls.env["stock.rule"].create(
            {
                "name": "Lead Time Manufacture Rule",
                "action": "manufacture",
                "location_dest_id": cls.warehouse.lot_stock_id.id,
                "picking_type_id": cls.warehouse.manu_type_id.id,
                "company_id": cls.env.company.id,
                "route_id": cls.env.ref("mrp.route_warehouse0_manufacture").id,
            }
        )

    def test_prepare_mo_vals_uses_sale_line_mfg_lead_time(self):
        delivery_date = datetime(2026, 7, 20, 17, 0, 0)
        values = {
            "date_planned": delivery_date,
            "date_deadline": delivery_date,
            "warehouse_id": self.warehouse,
            "mfg_lead_time": 5,
        }

        vals = self.rule._prepare_mo_vals(
            self.product,
            1.0,
            self.uom,
            self.warehouse.lot_stock_id,
            self.product.display_name,
            "SO-LEAD-TIME",
            self.env.company,
            values,
            self.bom,
        )

        self.assertEqual(vals["date_deadline"], delivery_date)
        self.assertEqual(vals["date_start"], delivery_date - relativedelta(days=5))
