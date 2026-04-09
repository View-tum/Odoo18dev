from odoo import fields, models

class ContractRebateGroup(models.Model):
    _name = "contract.rebate.group"
    _description = "Rebate Customer Group"

    name = fields.Char(string="Group Name", required=True)
    partner_ids = fields.Many2many(
        "res.partner",
        string="Customers",
        domain="['|', ('company_id', '=', False), ('company_id', '=', parent.company_id)]",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
    )
