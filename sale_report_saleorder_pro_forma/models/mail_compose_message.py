# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import UserError

class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

    def _get_active_sale_orders(self):
        ctx = self.env.context
        if ctx.get("active_model") != "sale.order":
            raise UserError(_("This action is only available for Sale Orders."))
        ids = ctx.get("active_ids") or []
        if not ids:
            raise UserError(_("No Sale Order selected."))
        return self.env["sale.order"].browse(ids)

    def _run_jasper_direct(self, orders, fmt="pdf", lang=None):
        lang = lang or self.env.lang

        jasper_report = self.env["jasper.report"].browse(102)
        if not jasper_report.exists():
            raise UserError(_("Jasper report not found (id=102)."))

        ctx = dict(self.env.context or {})
        ctx.update({
            "doc_model": "sale.order",
            "docids": orders.ids,
            "params": {
                "sale_order_ids": ",".join(map(str, orders.ids)),
                "docid": orders[:1].id,
                "lang": lang,
                "company_id": self.env.company.id,
            },
        })

        # 1️⃣ สร้าง wizard record
        wizard = self.env["jasper.report.run"].with_context(ctx).create({
            "report_id": jasper_report.id,
            "format": fmt,
            "preview": False,
        })

        # 2️⃣ เรียก print ทันที
        return wizard.run_report()

    def _run_jasper_direct_th(self, orders, fmt="pdf", lang=None):
        lang = lang or self.env.lang

        jasper_report = self.env["jasper.report"].browse(103)
        if not jasper_report.exists():
            raise UserError(_("Jasper report not found (id=103)."))

        ctx = dict(self.env.context or {})
        ctx.update({
            "doc_model": "sale.order",
            "docids": orders.ids,
            "params": {
                "sale_order_ids": ",".join(map(str, orders.ids)),
                "docid": orders[:1].id,
                "lang": lang,
                "company_id": self.env.company.id,
            },
        })

        # 1️⃣ สร้าง wizard record
        wizard = self.env["jasper.report.run"].with_context(ctx).create({
            "report_id": jasper_report.id,
            "format": fmt,
            "preview": False,
        })

        # 2️⃣ เรียก print ทันที
        return wizard.run_report()

    def action_custom_proforma_export_pdf(self):
        orders = self._get_active_sale_orders()
        return self._run_jasper_direct(orders, fmt="pdf", lang="en_US")

    def action_custom_proforma_export_pdf_th(self):
        orders = self._get_active_sale_orders()
        return self._run_jasper_direct_th(orders, fmt="pdf", lang="th_TH")
