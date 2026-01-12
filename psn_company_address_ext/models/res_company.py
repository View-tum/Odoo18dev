# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    name_en = fields.Char(string="Name (EN)")
    street_en = fields.Char(string="Street (EN)")
    street2_en = fields.Char(string="Street (EN)")
    zip_en = fields.Char(string="Zip (EN)")
    city_en = fields.Char(string="Street (EN)")
    state_id_en = fields.Char(string='Fed. State (EN)')
    country_id_en = fields.Char(string='Country (EN)')

