from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    allow_quick_create = fields.Boolean(
        string="Allow Quick Create",
        default=True,
        help="If unchecked, the user will not see 'Create' and 'Create and edit...' "
             "options in Many2one dropdown fields. This prevents accidental creation "
             "of new records when typing non-existent values.",
    )

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ["allow_quick_create"]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ["allow_quick_create"]
