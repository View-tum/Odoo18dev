# -*- coding: utf-8 -*-
from odoo import api, models
from odoo.osv import expression


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def _group_payment_name_search_result(self, records, limit=100):
        """Return name_search-style tuples in Odoo 18+ without relying on name_get()."""
        records = records[:limit]
        return [(rec.id, rec.display_name) for rec in records]

    @api.model
    def _group_payment_root_group_domain(self):
        """Root company groups in current project may be flagged in two ways.

        Some records use is_company_group=True, others are roots because they
        are referenced by member.company_group_id.

        Avoid searching on company_group_company_ids because that O2M carries a
        domain on non-stored field company_type in this project, which causes
        `Non-stored field res.partner.company_type cannot be searched`.
        """
        return [("is_company_group", "=", True)]

    @api.model
    def _is_group_payment_company_group_lookup(self, args):
        return bool(self.env.context.get("group_payment_company_group_search"))

    @api.model
    def _search_group_payment_root_candidates(self, args=None, limit=100):
        """Return root groups including roots implied by member.company_group_id."""
        args = args or []
        safe_self = self.with_context(group_payment_company_group_search=False)
        limit = limit or 100
        roots = safe_self.search(expression.AND([args, self._group_payment_root_group_domain()]), limit=max(limit * 5, 50))
        # Fallback: derive roots from any visible member links in case root flags are incomplete.
        member_candidates = safe_self.search(
            expression.AND([args, [("company_group_id", "!=", False)]]),
            limit=max(limit * 20, 200),
        )
        roots |= member_candidates.mapped("company_group_id")
        return roots

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        """Search company groups by root-group name or member-company name.

        This is used only by the Group Payment company_group_id field via context flag.
        The field stores the root group, but users often type a member company name.
        """
        if not self._is_group_payment_company_group_lookup(args):
            return super().name_search(name=name, args=args, operator=operator, limit=limit)

        args = args or []
        safe_self = self.with_context(group_payment_company_group_search=False)
        limit = limit or 100

        roots_all = self._search_group_payment_root_candidates(args=args, limit=limit)

        if not name:
            ordered_roots = roots_all.sorted(lambda p: (p.name or "").casefold())
            return self._group_payment_name_search_result(ordered_roots, limit=limit)

        fetch_limit = max(limit * 5, 20)
        standard_candidates = safe_self.search(
            expression.AND([args, [("name", operator, name)]]),
            limit=fetch_limit,
        )
        root_hits = safe_self.search(
            expression.AND([args, [("id", "in", roots_all.ids), ("name", operator, name)]]),
            limit=fetch_limit,
        ) if roots_all else safe_self.browse()
        member_hits = safe_self.search(
            expression.AND([args, [("company_group_id", "!=", False), ("name", operator, name)]]),
            limit=max(limit * 10, 50),
        )

        candidates = (standard_candidates | root_hits | member_hits | member_hits.mapped("company_group_id"))
        roots = candidates.filtered(lambda p: p.is_company_group or bool(p.company_group_company_ids))
        roots |= candidates.filtered(lambda p: p.company_group_id).mapped("company_group_id")

        typed = (name or "").strip().casefold()

        def _rank_key(partner):
            partner_name = (partner.name or "").strip().casefold()
            if partner_name == typed:
                return (0, partner_name)
            if partner_name.startswith(typed):
                return (1, partner_name)
            return (2, partner_name)

        ordered_roots = roots.sorted(key=_rank_key)
        return self._group_payment_name_search_result(ordered_roots, limit=limit)
