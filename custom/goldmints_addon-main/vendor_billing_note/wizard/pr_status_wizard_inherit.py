from odoo import _, models
from odoo.exceptions import UserError


class PurchaseRequestStatusReportWizard(models.TransientModel):
    _inherit = "purchase.request.status.report.wizard"

    def action_create_billing_note(self):
        self.ensure_one()
        report = self.env["report.purchase_request_status_report.pr_status_report"]
        lines = report._get_lines(self)
        billable_lines = [
            line for line in lines
            if line.get("billing_note_status") in ("ready", "partial")
            and line.get("qty_to_billing_note", 0.0) > 0.001
        ]
        if not billable_lines:
            raise UserError(_("No received purchase order lines are available for a vendor billing note."))

        vendors = {line["vendor"].id for line in billable_lines if line.get("vendor")}
        if len(vendors) != 1:
            raise UserError(_("Please filter or select one vendor before creating a vendor billing note."))

        billing_data = []
        for line in billable_lines:
            for po_line in line["po_lines"]:
                qty_to_bill = po_line._get_qty_to_billing_note()
                if qty_to_bill > 0.001:
                    billing_data.append({
                        "purchase_line_id": po_line.id,
                        "quantity": qty_to_bill,
                    })

        if not billing_data:
            raise UserError(_("No remaining received quantity is available for a vendor billing note."))

        return self.env["purchase.order"].action_create_billing_note_from_data(
            next(iter(vendors)),
            billing_data,
        )


class PurchaseRequestStatusReport(models.AbstractModel):
    _inherit = "report.purchase_request_status_report.pr_status_report"

    def _get_lines(self, wizard):
        lines = super()._get_lines(wizard)
        for line in lines:
            po_lines = line["line"].purchase_lines.filtered(
                lambda po_line: po_line.state != "cancel"
                and po_line.order_id.state in ("purchase", "done")
                and po_line.display_type not in ("line_section", "line_note")
            )
            qty_received = sum(po_lines.mapped("qty_received"))
            qty_billing_noted = sum(po_lines.mapped("qty_billing_noted"))
            qty_billing_basis = sum(po_line._get_billing_note_qty_basis() for po_line in po_lines)
            qty_to_billing_note = sum(
                po_line._get_qty_to_billing_note()
                for po_line in po_lines
            )

            if not po_lines or qty_billing_basis <= 0.001:
                billing_note_status = "not_ready"
                billing_note_status_label = _("Not Received")
            elif qty_to_billing_note <= 0.001:
                billing_note_status = "done"
                billing_note_status_label = _("Billing Note Done")
            elif qty_billing_noted > 0.001:
                billing_note_status = "partial"
                billing_note_status_label = _("Partially Billing Noted")
            else:
                billing_note_status = "ready"
                billing_note_status_label = _("Ready for Billing Note")

            line.update({
                "po_lines": po_lines,
                "qty_received": qty_received,
                "qty_billing_noted": qty_billing_noted,
                "qty_to_billing_note": qty_to_billing_note,
                "billing_note_status": billing_note_status,
                "billing_note_status_label": billing_note_status_label,
                "billing_note_names": ", ".join(po_lines.mapped("billing_note_line_ids.billing_note_id.name")),
            })
        return lines
