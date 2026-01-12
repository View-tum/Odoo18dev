# -*- coding: utf-8 -*-
from odoo import fields, models

class Warranty(models.Model):
    _name = "warranty"
    _description = "Warranty"

    name = fields.Char(string="Warranty Name", required=True)
    description = fields.Text(string="Description")

