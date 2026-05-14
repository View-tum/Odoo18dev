from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ServiceAcceptance(models.Model):
    _inherit = 'service.acceptance'

    billing_note_ids = fields.One2many(
        "vendor.billing.note",
        "service_acceptance_id",
        string="Billing Notes",
    )
    billing_note_count = fields.Integer(
        string="Billing Notes Count",
        compute="_compute_billing_note_count",
    )
    is_billing_note_ready = fields.Boolean(
        compute="_compute_is_billing_note_ready",
        string="Is Billing Note Ready",
    )

    @api.depends("billing_note_ids")
    def _compute_billing_note_count(self):
        for rec in self:
            rec.billing_note_count = len(rec.billing_note_ids)

    @api.depends("state", "acceptance_line_ids.qty_accepted")
    def _compute_is_billing_note_ready(self):
        for rec in self:
            if rec.state != 'done':
                rec.is_billing_note_ready = False
            else:
                # Can create billing if there is at least one line with accepted qty > 0
                rec.is_billing_note_ready = any(
                    line.qty_accepted > 0 for line in rec.acceptance_line_ids
                )

    def action_create_billing_note(self):
        self.ensure_one()

        if self.state != 'done':
            raise UserError(_("สามารถวางบิลได้เฉพาะใบตรวจรับงานที่ 'ตรวจรับแล้ว' (Done) เท่านั้น"))

        lines_to_bill = self.acceptance_line_ids.filtered(lambda l: l.qty_accepted > 0)

        if not lines_to_bill:
            raise UserError(_("ไม่มีรายการที่สามารถวางบิลได้ (จำนวนที่ตรวจรับเป็น 0)"))

        note_lines = []
        for line in lines_to_bill:
            note_lines.append(
                (
                    0,
                    0,
                    {
                        "purchase_line_id": line.po_line_id.id,
                        "service_acceptance_id": self.id,
                        "name": line.name,
                        "quantity": line.qty_accepted,
                        "price_unit": line.price_unit,
                        "tax_ids": [(6, 0, line.po_line_id.taxes_id.ids)] if line.po_line_id.taxes_id else False,
                    },
                )
            )

        billing_note = self.env["vendor.billing.note"].create({
            "partner_id": self.partner_id.id,
            "service_acceptance_id": self.id,
            "line_ids": note_lines,
        })

        return {
            "name": _("Billing Note"),
            "type": "ir.actions.act_window",
            "res_model": "vendor.billing.note",
            "view_mode": "form",
            "res_id": billing_note.id,
            "target": "current",
        }

    def action_view_billing_notes(self):
        self.ensure_one()
        return {
            "name": _("Billing Notes"),
            "type": "ir.actions.act_window",
            "res_model": "vendor.billing.note",
            "view_mode": "list,form",
            "domain": [("service_acceptance_id", "=", self.id)],
            "context": {"default_service_acceptance_id": self.id, "default_partner_id": self.partner_id.id},
        }
