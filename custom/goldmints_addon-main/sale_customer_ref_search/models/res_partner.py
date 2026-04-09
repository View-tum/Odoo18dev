from odoo import api, models
from odoo.osv import expression


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _compute_display_name(self):
        """
        Keep default display (including full address) then prefix with ref when
        the sale-specific context flag is present.
        """
        super()._compute_display_name()
        if not self.env.context.get("show_sale_ref_name"):
            return

        for partner in self:
            if partner.ref and partner.display_name:
                partner.display_name = f"{partner.ref} -> {partner.display_name}"

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        """Show partner ref before name and prioritize exact ref hits in sale customer lookup."""
        args = args or []
        if not self.env.context.get("show_sale_ref_name"):
            return super().name_search(name=name, args=args, operator=operator, limit=limit)

        # Keep Odoo's standard search behavior, but force full address in labels.
        partner_ctx = self.with_context(show_address=True)

        # When users type an exact customer ref (e.g. "01255"), return those
        # matches first so duplicate refs are all visible in autocomplete.
        cleaned_name = (name or "").strip()
        positive_ops = {"ilike", "like", "=", "=ilike", "=like"}
        if cleaned_name and operator in positive_ops:
            contact_or_empty_type_domain = [
                "|",
                ("type", "=", False),
                ("type", "=", "contact"),
            ]
            exact_ref_partners = partner_ctx.search(
                expression.AND([args, [("ref", "=ilike", cleaned_name)], contact_or_empty_type_domain]),
                limit=False,
            )
            if exact_ref_partners:
                return [(partner.id, partner.display_name) for partner in exact_ref_partners]

        return super(ResPartner, partner_ctx).name_search(
            name=name,
            args=args,
            operator=operator,
            limit=limit,
        )
