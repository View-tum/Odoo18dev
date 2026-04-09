# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import  fields, models

class MassActionpartnerWizard(models.TransientModel):
    _name = "sh.partners.config.mass.update"
    _description = "Partners Statement Mass Update"

    sh_partners_config_update = fields.Selection(
        [("add", "Add"), ("remove", "Remove")],
        string="Partners Statement Action",
        default="add",
    )
    sh_update_config_ids = fields.Many2many(
        "sh.statement.config", string="Config", required=True
    )
    sh_selected_partner_ids = fields.Many2many(
        "res.partner", string="Selected partners"
    )

    # Update Customers Statement Config
    def update_partners_config(self):
        if self.sh_partners_config_update == "add":
            for record in self.sh_update_config_ids:
                for partner in self.sh_selected_partner_ids:
                    if partner.customer_rank >= 1:
                        if partner not in record.sh_customer_partner_ids:
                            record.write({"sh_customer_partner_ids": [(4, partner.id)]})
                            partner.sh_customer_statement_config = [(4, record.id)]
                    if partner.supplier_rank >= 1:
                        if partner not in record.sh_vendor_partner_ids:
                            record.write({"sh_vendor_partner_ids": [(4, partner.id)]})
                            partner.sh_vendor_statement_config = [(4, record.id)]
        else:
            for record in self.sh_update_config_ids:
                for partner in self.sh_selected_partner_ids:
                    if partner.customer_rank >= 1:
                        if partner in record.sh_customer_partner_ids:
                            record.sh_customer_partner_ids = [(3, partner.id)]
                            partner.sh_customer_statement_config = [(3, record.id)]
                    if partner.supplier_rank >= 1:
                        if partner in record.sh_vendor_partner_ids:
                            record.sh_vendor_partner_ids = [(3, partner.id)]
                            partner.sh_vendor_statement_config = [(3, record.id)]
