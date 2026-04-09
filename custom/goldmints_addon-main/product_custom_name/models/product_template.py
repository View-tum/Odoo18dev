# -*- coding: utf-8 -*-
import re
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    # 4 reference segments
    ref_seg1 = fields.Char(
        string="Segment 1",
        size=2,
        help="Letters only, up to 2 characters.",
    )
    ref_seg2 = fields.Char(
        string="Segment 2",
        size=3,
        help="Letters only, up to 3 characters.",
    )
    ref_seg3 = fields.Char(
        string="Segment 3",
        size=2,
        help="Letters only, up to 2 characters.",
    )
    ref_seg4 = fields.Char(
        string="Segment 4",
        help="Digits only, no length limit.",
    )

    old_default_code = fields.Char(
        string="Reference Note",
        copy=False,
        help="Free-form note for reference/codes.",
    )

    old_default_product = fields.Char(
        string="Reference Product",
        copy=False,
        help="Free-form note for reference/product.",
    )

    @api.constrains("ref_seg1", "ref_seg2", "ref_seg3", "ref_seg4")
    def _check_segments(self):
        for rec in self:
            if rec.ref_seg1 and not re.fullmatch(r"[A-Za-zก-๙]{1,2}", rec.ref_seg1):
                raise ValidationError("Segment 1 must be letters only, max 2.")
            if rec.ref_seg2 and not re.fullmatch(r"[A-Za-zก-๙]{1,3}", rec.ref_seg2):
                raise ValidationError("Segment 2 must be letters only, max 3.")
            if rec.ref_seg3 and not re.fullmatch(r"[A-Za-zก-๙]{1,2}", rec.ref_seg3):
                raise ValidationError("Segment 3 must be letters only, max 2.")
            if rec.ref_seg4 and not re.fullmatch(r"\d+", rec.ref_seg4):
                raise ValidationError("Segment 4 must be digits only.")

    def _get_combined_reference(self, vals=None):
        self.ensure_one()
        seg1 = (vals or {}).get("ref_seg1", self.ref_seg1)
        seg2 = (vals or {}).get("ref_seg2", self.ref_seg2)
        seg3 = (vals or {}).get("ref_seg3", self.ref_seg3)
        seg4 = (vals or {}).get("ref_seg4", self.ref_seg4)
        parts = [p for p in (seg1, seg2, seg3, seg4) if p]
        return "-".join(parts) if parts else False

    @api.onchange("ref_seg1", "ref_seg2", "ref_seg3", "ref_seg4")
    def _onchange_segments_set_default_code(self):
        for rec in self:
            rec.default_code = rec._get_combined_reference()


    @api.model
    def create(self, vals):
        combined = "-".join(
            p for p in (vals.get("ref_seg1"), vals.get("ref_seg2"),
                        vals.get("ref_seg3"), vals.get("ref_seg4")) if p
        )
        if combined:
            vals = dict(vals, default_code=combined)
        return super().create(vals)

    def write(self, vals):
            res = super().write(vals)
            for rec in self:
                combined = rec._get_combined_reference()
                target = combined or False
                if rec.default_code != target:
                    super(ProductTemplate, rec).write({"default_code": target})
            return res
