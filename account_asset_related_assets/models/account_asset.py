from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountAsset(models.Model):
    _inherit = "account.asset"

    related_asset_ids = fields.Many2many(
        comodel_name="account.asset",
        relation="account_asset_relation_rel",
        column1="asset_id",
        column2="related_asset_id",
        string="Related Assets",
        help="Link other assets that should be considered together.",
    )
    child_asset_ids = fields.Many2many(
        comodel_name="account.asset",
        compute="_compute_child_asset_ids",
        inverse="_inverse_child_asset_ids",
        string="Child Assets",
        domain="[('id', '!=', id)]",
        help="Quickly manage the children of this asset without opening each child.",
    )
    is_parent_asset = fields.Boolean(
        compute="_compute_hierarchy_flags",
        string="Is Parent Asset",
        help="Technical flag to mark assets that have children.",
    )
    is_child_asset = fields.Boolean(
        compute="_compute_hierarchy_flags",
        string="Is Child Asset",
        help="Technical flag to mark assets that have a parent.",
    )
    child_count = fields.Integer(
        compute="_compute_hierarchy_flags",
        string="Child Asset Count",
        help="Number of child assets.",
    )
    has_child_assets = fields.Boolean(
        compute="_compute_hierarchy_flags",
        string="Has Child Assets",
        help="Technical flag to mark assets that have children.",
    )
    hierarchy_related_asset_ids = fields.Many2many(
        comodel_name="account.asset",
        compute="_compute_hierarchy_related_asset_ids",
        string="Related Assets (Hierarchy)",
        help="Shows children if they exist, otherwise the parent asset.",
    )

    @api.constrains("related_asset_ids")
    def _check_no_self_relation(self):
        for asset in self:
            if asset in asset.related_asset_ids:
                raise ValidationError(_("An asset cannot be related to itself."))

    @api.constrains("parent_id")
    def _check_parent_cycle(self):
        for asset in self:
            seen = set()
            current = asset.parent_id
            while current:
                if current.id in seen or current == asset:
                    raise ValidationError(_("Circular asset hierarchy is not allowed."))
                seen.add(current.id)
                current = current.parent_id

    def _compute_child_asset_ids(self):
        for asset in self:
            asset.child_asset_ids = asset.children_ids

    def _inverse_child_asset_ids(self):
        for asset in self:
            desired_children = asset.child_asset_ids
            current_children = asset.children_ids
            to_add = desired_children - current_children
            to_remove = current_children - desired_children

            for child in to_add:
                self._assert_no_hierarchy_cycle(asset, child)
            to_add.write({"parent_id": asset.id})
            to_remove.write({"parent_id": False})

    def _assert_no_hierarchy_cycle(self, parent_asset, child_asset):
        """Prevent assigning an ancestor as a child, creating a cycle."""
        current = parent_asset
        while current:
            if current == child_asset:
                raise ValidationError(_("Cannot set a parent as its own child asset."))
            current = current.parent_id

    def _compute_hierarchy_related_asset_ids(self):
        for asset in self:
            if asset.children_ids:
                asset.hierarchy_related_asset_ids = asset.children_ids
            elif asset.parent_id:
                asset.hierarchy_related_asset_ids = asset.parent_id
            else:
                asset.hierarchy_related_asset_ids = False

    @api.depends("related_asset_ids")
    def _compute_hierarchy_flags(self):
        for asset in self:
            rel_count = len(asset.related_asset_ids - asset)
            asset.child_count = rel_count
            asset.has_child_assets = rel_count > 0
            asset.is_parent_asset = rel_count > 1
            asset.is_child_asset = bool(asset.parent_id) or rel_count == 1
            # Auto-link related assets as children when this record acts as a parent
            if asset.is_parent_asset and not asset.parent_id:
                asset._assign_related_as_children()

    def _assign_related_as_children(self):
        """Assign parent_id to related assets that have no parent (or already point here)."""
        self.ensure_one()
        candidates = self.related_asset_ids - self
        if not candidates:
            return
        to_link = candidates.filtered(
            lambda r: not r.parent_id or r.parent_id == self
        )
        if to_link:
            to_link.with_context(skip_related_asset_sync=True).write({"parent_id": self.id})

    def _sync_related_assets(self, previous_links=None):
        """Keep related links symmetrical on both sides."""
        self.ensure_one()
        if self.env.context.get("skip_related_asset_sync"):
            return

        previous_links = (previous_links or self.env["account.asset"]) - self
        new_links = self.related_asset_ids - self
        added = new_links - previous_links
        removed = previous_links - new_links

        for related in added:
            related.with_context(skip_related_asset_sync=True).write(
                {"related_asset_ids": [(4, self.id)]}
            )
        for related in removed:
            related.with_context(skip_related_asset_sync=True).write(
                {"related_asset_ids": [(3, self.id)]}
            )

    @api.model
    def create(self, vals):
        asset = super().create(vals)
        if "related_asset_ids" in vals:
            asset._sync_related_assets()
            if not asset.parent_id and asset.related_asset_ids:
                safe_children = asset.related_asset_ids.filtered(
                    lambda c: not c.parent_id or c.parent_id == asset
                )
                for child in safe_children:
                    asset._assert_no_hierarchy_cycle(asset, child)
                if safe_children:
                    safe_children.write({"parent_id": asset.id})
        return asset

    def write(self, vals):
        if self.env.context.get("skip_related_asset_sync"):
            return super().write(vals)

        previous_relations = {}
        previous_children = {}
        related_update = "related_asset_ids" in vals
        if related_update:
            for asset in self:
                previous_relations[asset.id] = asset.related_asset_ids
                previous_children[asset.id] = asset.child_asset_ids

        res = super().write(vals)

        if related_update:
            for asset in self:
                asset._sync_related_assets(previous_relations.get(asset.id))
                if not asset.parent_id:
                    desired_children = asset.related_asset_ids - asset
                    prev_children = previous_children.get(asset.id, self.env["account.asset"])
                    to_add = desired_children - prev_children
                    to_remove = prev_children - desired_children
                    safe_to_add = to_add.filtered(lambda c: not c.parent_id or c.parent_id == asset)
                    for child in safe_to_add:
                        self._assert_no_hierarchy_cycle(asset, child)
                    if safe_to_add:
                        safe_to_add.write({"parent_id": asset.id})
                    if to_remove:
                        to_remove.write({"parent_id": False})
        return res

    def _raise_related_asset_alert(self, action_label):
        """Raise an alert if assets still have linked assets outside current batch."""
        for asset in self:
            linked_assets = (
                asset.related_asset_ids | asset.child_asset_ids | asset.parent_id
            ) - self
            if linked_assets:
                related_names = ", ".join(linked_assets.mapped("display_name"))
                raise UserError(
                    _(
                        "Asset %(asset)s is linked to other assets: %(related)s. "
                        "Review or unlink them before %(action)s."
                    )
                    % {
                        "asset": asset.display_name,
                        "related": related_names,
                        "action": action_label,
                    }
                )

    def unlink(self):
        self._raise_related_asset_alert(_("deleting it"))
        return super().unlink()

    def set_to_close(self, invoice_line_ids, date=None, message=None):
        """Stop disposal/sale if other related assets still exist."""
        self._raise_related_asset_alert(_("disposing or selling it"))
        return super().set_to_close(invoice_line_ids, date=date, message=message)
