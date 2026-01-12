from odoo import api, models


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
        """Show partner ref before name when the context flag is set (sale order customer search)."""
        args = args or []
        if not self.env.context.get("show_sale_ref_name"):
            return super().name_search(name=name, args=args, operator=operator, limit=limit)

        # Let base logic build labels, but force full address in the display.
        # _compute_display_name will add the ref prefix once via context flag.
        return super(ResPartner, self.with_context(show_address=True)).name_search(
            name=name, args=args, operator=operator, limit=limit
        )
