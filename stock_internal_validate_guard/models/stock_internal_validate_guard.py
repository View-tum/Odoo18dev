# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import AccessError


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    enforce_internal_validate_restriction = fields.Boolean(
        string="Enforce Validate Restriction (Internal Only)",
        help="When enabled (and this is an Internal operation type), only allowed groups can validate Internal Transfers."
    )
    allowed_validate_group_ids = fields.Many2many(
        "res.groups",
        "stock_picking_type_allowed_validate_group_rel",
        "picking_type_id",
        "group_id",
        string="Allowed Groups to Validate",
        help="Users in these groups can validate Internal Transfers of this Operation Type."
    )
    allow_admin_bypass = fields.Boolean(
        string="Allow Inventory Administrators Bypass",
        help="If enabled, Inventory Managers can always validate regardless of the allowed groups."
    )
    
    is_internal_picking = fields.Boolean(
    string="Is Internal Picking",
    compute="_compute_is_internal_picking",
    compute_sudo=False,
    )

    @api.depends("code")
    def _compute_is_internal_picking(self):
        for rec in self:
            rec.is_internal_picking = rec.code == "internal"

    def _internal_validate_restriction_is_active(self):
        """Return True if restriction is active for this op type (i.e., internal + enforce flag)."""
        self.ensure_one()
        return self.code == "internal" and self.enforce_internal_validate_restriction


class StockPicking(models.Model):
    _inherit = "stock.picking"

    is_internal_picking = fields.Boolean(
        related="picking_type_id.is_internal_picking",
        string="Is Internal Picking",
        readonly=True,
        store=False,
    )
    can_validate_by_group = fields.Boolean(
        string="Can Validate (by Group Policy)",
        compute="_compute_can_validate_by_group",
        help="Computed access to show/hide the Validate button. Also enforced server-side."
    )

    @api.depends("picking_type_id.enforce_internal_validate_restriction",
                 "picking_type_id.allowed_validate_group_ids",
                 "picking_type_id.allow_admin_bypass")
    def _compute_can_validate_by_group(self):
        """Compute whether current user can validate this picking."""
        user = self.env.user
        group_stock_manager = self.env.ref("stock.group_stock_manager", raise_if_not_found=False)
        for picking in self:
            pt = picking.picking_type_id
            # Default: allowed if not internal flow or no restriction
            allowed = True
            if pt and pt._internal_validate_restriction_is_active():
                allowed = False
                # Admin bypass
                if pt.allow_admin_bypass and group_stock_manager and group_stock_manager in user.groups_id:
                    allowed = True
                # Allowed groups
                elif pt.allowed_validate_group_ids and (pt.allowed_validate_group_ids & user.groups_id):
                    allowed = True
            picking.can_validate_by_group = allowed

    def _check_internal_validate_rights(self):
        """Server-side guard to prevent unauthorized validation."""
        self.ensure_one()
        pt = self.picking_type_id
        if not pt or pt.code != "internal":
            return  # Only restrict Internal Transfers
        if not pt._internal_validate_restriction_is_active():
            return

        user = self.env.user
        group_stock_manager = self.env.ref("stock.group_stock_manager", raise_if_not_found=False)

        # Admin bypass
        if pt.allow_admin_bypass and group_stock_manager and group_stock_manager in user.groups_id:
            return

        # Allowed groups
        if pt.allowed_validate_group_ids and (pt.allowed_validate_group_ids & user.groups_id):
            return

        # If we reach here, not allowed
        raise AccessError(
            _("You are not allowed to validate this Internal Transfer. Please contact your administrator.")
        )

    def button_validate(self):
        """Override to enforce restriction server-side."""
        for picking in self:
            picking._check_internal_validate_rights()
        return super().button_validate()


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    internal_validate_lines = fields.One2many(
        "stock.internal.validate.settings.line",
        "settings_id",
        string="Internal Types Validate Control",
        help="Configure allowed groups for Internal Operation Types."
    )

    def _default_internal_lines(self):
        """Read current config from all internal operation types."""
        types = self.env["stock.picking.type"].sudo().search([("code", "=", "internal")], order="sequence,id")
        lines = []
        for t in types:
            lines.append((0, 0, {
                "picking_type_id": t.id,
                "name": t.name,
                "enforce": t.enforce_internal_validate_restriction,
                "allow_admin_bypass": t.allow_admin_bypass,
                "allowed_group_ids": [(6, 0, t.allowed_validate_group_ids.ids)],
            }))
        return lines

    @api.model
    def default_get(self, fields_list):
        """Populate One2many with current values for quick editing in Settings."""
        res = super().default_get(fields_list)
        if "internal_validate_lines" in fields_list:
            res["internal_validate_lines"] = self._default_internal_lines()
        return res

    def set_values(self):
        """Apply edited Settings lines back to stock.picking.type records."""
        super().set_values()
        for settings in self:
            for line in settings.internal_validate_lines:
                if not line.picking_type_id or line.picking_type_id.code != "internal":
                    continue
                line.picking_type_id.sudo().write({
                    "enforce_internal_validate_restriction": line.enforce,
                    "allow_admin_bypass": line.allow_admin_bypass,
                    "allowed_validate_group_ids": [(6, 0, line.allowed_group_ids.ids)],
                })


class StockInternalValidateSettingsLine(models.TransientModel):
    """Transient helper lines to batch-edit Internal Operation Types in Settings."""
    _name = "stock.internal.validate.settings.line"
    _description = "Internal Transfer Validate Settings Line"

    settings_id = fields.Many2one("res.config.settings", ondelete="cascade")
    name = fields.Char(string="Operation Type", readonly=True)
    picking_type_id = fields.Many2one(
        "stock.picking.type",
        string="Operation Type",
        domain="[(\'code\',\'=\',\'internal\')]",
        required=True,
        readonly=True,
        help="Internal Operation Type."
    )
    enforce = fields.Boolean(
        string="Enforce",
        help="Enable restriction for this Internal Operation Type."
    )
    allow_admin_bypass = fields.Boolean(
        string="Admin Bypass",
        help="Allow Inventory Managers to validate regardless of allowed groups."
    )
    allowed_group_ids = fields.Many2many(
        "res.groups",
        "stock_internal_validate_line_group_rel",
        "line_id",
        "group_id",
        string="Allowed Groups",
        help="Users in these groups can validate Internal Transfers of this Operation Type."
    )
