from odoo import models, fields

class ResGroups(models.Model):
    _inherit = "res.groups"

    inherited_by_ids = fields.Many2many(
        "res.groups",
        string="Inherited By",
        relation='res_groups_implied_rel', 
        column1='hid',
        column2='gid'
    )