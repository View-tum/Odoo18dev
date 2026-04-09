# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class CRMClaimRejectMessage(models.Model):
    _name = 'claim.reject.message'
    _description = 'CRM Claim Reject Message'

    name = fields.Char("Reject Reason", required=1)


class CRMReason(models.Model):
    _name = 'rma.reason.ept'
    _description = 'CRM Reason'

    name = fields.Char("RMA Reason", required=1)
    code = fields.Char("Code", required=1)
    action = fields.Selection([
        ('refund', 'Refund'),
        ('replace_same_product', 'Replace With Same Product'),
        ('replace_other_product', 'Replace With Other Product'),
        ('repair', 'Repair')], string="Related Action")

    def _compute_display_name(self):
        super()._compute_display_name()
        if not self.env.context.get("show_rma_reason_code"):
            return

        for reason in self:
            if reason.code and reason.display_name:
                reason.display_name = f"{reason.code} -> {reason.display_name}"

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        """Show reason code before name when the context flag is set."""
        args = args or []
        if not self.env.context.get("show_rma_reason_code"):
            return super().name_search(name=name, args=args, operator=operator, limit=limit)

        domain = args
        if name:
            domain = ['|', ('name', operator, name), ('code', operator, name)] + args

        reasons = self.search_fetch(domain, ['display_name'], limit=limit)
        return [(reason.id, reason.display_name) for reason in reasons.sudo()]
