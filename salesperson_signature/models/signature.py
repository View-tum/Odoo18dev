# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CompanyStamp(models.Model):
    _inherit = "res.company"

    company_stamp = fields.Binary(string="Company Stamp")
    stamp_position = fields.Selection([('left', 'Left'), ('center', 'Center'), ('right', 'Right')],
                                      string="Stamp Position", default="left", ondelete="cascade")
