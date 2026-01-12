from odoo import models, fields

class ResGroups(models.Model):
    _inherit = "res.groups"

    approval_config_ids = fields.Many2many(
        "approval.config",
        string="Approval Status",
        relation='approval_config_group_ids_rel'
        )