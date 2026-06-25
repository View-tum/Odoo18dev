from odoo.tests import Form, tagged
from odoo.addons.mrp.tests.common import TestMrpCommon


@tagged("post_install", "-at_install", "sale_production_noti_intl")
class TestMoDoneNotification(TestMrpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {"name": "MO Done Notification Customer"}
        )
        cls.so_type = (
            cls.env.ref("sale_so_type.sale_sequence_type_international", False)
            or cls.env["sale.sequence.type"].search([], limit=1)
            or cls.env["sale.sequence.type"].create(
                {"name": "MO Done Notification Type", "market_scope": "domestic"}
            )
        )

    def _create_sale_order(self):
        return self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "user_id": self.env.user.id,
                "so_type_id": self.so_type.id,
            }
        )

    def _link_sale_to_mo(self, sale, mo):
        group = self.env["procurement.group"].create(
            {
                "name": sale.name,
                "sale_id": sale.id,
                "partner_id": sale.partner_shipping_id.id,
            }
        )
        mo.procurement_group_id = group

    def _activity_count(self, sale):
        return self.env["mail.activity"].search_count(
            [
                ("res_model", "=", "sale.order"),
                ("res_id", "=", sale.id),
                ("summary", "=", "MO Done: Goods Ready"),
            ]
        )

    def test_mo_done_creates_sales_activity_and_chatter_log_with_done_qty(self):
        mo, bom, finished_product, raw_1, raw_2 = self.generate_mo(qty_final=4)
        sale = self._create_sale_order()
        self._link_sale_to_mo(sale, mo)

        mo_form = Form(mo)
        mo_form.qty_producing = 4.0
        mo_form.save()

        before_messages = sale.message_ids
        mo.with_context(skip_consumption=True, skip_backorder=True).button_mark_done()

        self.assertEqual(mo.state, "done")
        self.assertEqual(self._activity_count(sale), 1)
        self.assertTrue(mo.sale_mo_done_notified)

        new_messages = sale.message_ids - before_messages
        message_body = " ".join(str(message.body) for message in new_messages)
        self.assertIn(mo.name, message_body)
        self.assertIn("4.00", message_body)
        self.assertIn(finished_product.display_name, message_body)

        mo._notify_linked_sale_orders_mo_done()
        self.assertEqual(self._activity_count(sale), 1)
