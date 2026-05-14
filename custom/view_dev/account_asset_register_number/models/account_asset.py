from odoo import api, fields, models, _

class AccountAsset(models.Model):
    _inherit = "account.asset"

    asset_register_number = fields.Char(
        string="เลขทะเบียนคุม FIX ASSET",
        readonly=True,
        copy=False,
        default=lambda self: _("New"),
        help="Auto-generated Fixed Asset Register Number",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("asset_register_number", _("New")) == _("New"):
                vals["asset_register_number"] = self.env["ir.sequence"].next_by_code("account.asset.register.number") or _("New")
        return super().create(vals_list)
