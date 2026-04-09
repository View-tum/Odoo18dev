from odoo import fields, models
from odoo.exceptions import UserError


class ResPartnerPayeeName(models.Model):
    _name = "res.partner.payee.name"
    _description = "Partner Payee Name"
    _order = "is_default desc, name"

    partner_id = fields.Many2one(
        "res.partner",
        string="Partner",
        required=True,
        ondelete="cascade",
        index=True,
    )
    name = fields.Char("Payee Name", required=True)
    is_default = fields.Boolean("Default (Partner Name)", default=False)

    _sql_constraints = [
        (
            "partner_name_uniq",
            "UNIQUE(partner_id, name)",
            "This payee name already exists for this partner.",
        ),
    ]

    def unlink(self):
        for rec in self:
            if rec.is_default:
                raise UserError(
                    "Cannot delete the default payee name '%s'. "
                    "This is the partner's own name." % rec.name
                )
        return super().unlink()
