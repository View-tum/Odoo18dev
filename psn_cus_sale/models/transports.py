# -*- coding: utf-8 -*-
from odoo import fields, models

class Transport(models.Model):
    _name = "transports"
    _description = "Transports"

    name = fields.Char(string="Transports Name", required=True)
    description = fields.Text(string="Description")
