# -*- coding: utf-8 -*-
from odoo import api, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _has_own_address(self):
        """Return True when the partner already has address data set."""
        self.ensure_one()
        return any(
            (
                self.street,
                self.street2,
                self.city,
                self.zip,
                self.state_id,
                self.country_id,
            )
        )

    @api.onchange("parent_id")
    def onchange_parent_id(self):
        """Preserve address values if the contact already has its own address."""
        res = super().onchange_parent_id() or {}
        values = dict(res.get("value") or {})
        if self and self._has_own_address():
            for key in ("street", "street2", "zip", "city", "state_id", "country_id"):
                values.pop(key, None)
        if self and self.vat:
            values.pop("vat", None)
        res["value"] = values
        return res

    def _commercial_sync_from_company(self):
        """Sync commercial fields but keep existing VAT values on child contacts."""
        children_with_vat = self.filtered(
            lambda partner: partner.commercial_partner_id != partner and partner.vat
        )
        others = self - children_with_vat

        if others:
            super(ResPartner, others)._commercial_sync_from_company()

        for partner in children_with_vat:
            commercial_partner = partner.commercial_partner_id
            if commercial_partner == partner:
                continue
            sync_vals = commercial_partner._update_fields_values(partner._commercial_fields())
            sync_vals.pop("vat", None)
            partner.write(sync_vals)
            partner._company_dependent_commercial_sync()
            partner._commercial_sync_to_children()
