from odoo import api, models


class CrmClaimEpt(models.Model):
    _inherit = "crm.claim.ept"

    @api.onchange("picking_id")
    def onchange_picking_id_sync_invoice_info(self):
        if self.picking_id and self.return_picking_id:
            self.return_picking_id.write({
                "invoice_reference": self.picking_id.invoice_reference,
                "invoice_date": self.picking_id.invoice_date,
            })

    def write(self, vals):
        res = super().write(vals)
        if "picking_id" in vals:
            for record in self:
                if record.picking_id and record.return_picking_id:
                    record.return_picking_id.write({
                        "invoice_reference": record.picking_id.invoice_reference,
                        "invoice_date": record.picking_id.invoice_date,
                    })
        return res
