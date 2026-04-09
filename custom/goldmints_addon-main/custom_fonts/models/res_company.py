
from odoo import fields, models


class Company(models.Model):
    _inherit = "res.company"

    font = fields.Selection(
        selection_add=[
            ("Kanit-Black", "Kanit-Black"),
            ("Kanit-BlackItalic", "Kanit-BlackItalic"),
            ("Kanit-Bold", "Kanit-Bold"),
            ("Kanit-BoldItalic", "Kanit-BoldItalic"),
            ("Kanit-ExtraBold", "Kanit-ExtraBold"),
            ("Kanit-ExtraBoldItalic", "Kanit-ExtraBoldItalic"),
            ("Kanit-ExtraLight", "Kanit-ExtraLight"),
            ("Kanit-ExtraLightItalic", "Kanit-ExtraLightItalic"),
            ("Kanit-Italic", "Kanit-Italic"),
            ("Kanit-Light", "Kanit-Light"),
            ("Kanit-LightItalic", "Kanit-LightItalic"),
            ("Kanit-Medium", "Kanit-Medium"),
            ("Kanit-MediumItalic", "Kanit-MediumItalic"),
            ("Kanit-Regular", "Kanit-Regular"),
            ("Kanit-SemiBold", "Kanit-SemiBold"),
            ("Kanit-SemiBoldItalic", "Kanit-SemiBoldItalic"),
            ("Kanit-Thin", "Kanit-Thin"),
            ("Kanit-ThinItalic", "Kanit-ThinItalic"),
            ("CORDIA", "CORDIA")
        ]
    )