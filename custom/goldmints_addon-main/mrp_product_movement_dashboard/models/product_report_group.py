from collections import Counter

from odoo import _, api, fields, models


class ProductReportGroup(models.Model):
    _name = "product.report.group"
    _description = "Product Report Group"
    _order = "sequence, name"

    name = fields.Char(required=True)
    code = fields.Char(required=True, index=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    product_tmpl_ids = fields.One2many("product.template", "report_group_id", string="Products")

    _sql_constraints = [
        ("product_report_group_code_uniq", "unique(code)", "Product report group code must be unique."),
    ]

    @api.model
    def _default_group_definitions(self):
        return [
            {"code": "FG_PHARMA", "name": "FG Pharma", "sequence": 10},
            {"code": "FG_PLASTIC", "name": "FG Plastic", "sequence": 20},
            {"code": "SEMI_FINISHED", "name": "Semi Finished", "sequence": 30},
            {"code": "RM_CHEMICAL", "name": "RM Chemical", "sequence": 40},
            {"code": "RM_PACKAGING", "name": "RM Packaging", "sequence": 50},
            {"code": "OTHER_INV", "name": "Other Inventory", "sequence": 60},
        ]

    @api.model
    def _resolve_report_group_code(self, product_tmpl):
        category_name = (product_tmpl.categ_id.display_name or "").lower()
        default_code = (product_tmpl.default_code or "").upper()
        manufacturing_type = (getattr(product_tmpl, "manufacturing_type", "") or "").lower()

        if "/ sfg /" in category_name or "semi" in category_name:
            return "SEMI_FINISHED"

        if "/ rm / สารเคมี" in category_name or any(default_code.startswith(prefix) for prefix in ("005", "007", "008")):
            return "RM_CHEMICAL"

        if "/ rm / บรรจุภัณฑ์" in category_name or default_code.startswith("PK"):
            return "RM_PACKAGING"

        if "/ fg /" in category_name or default_code.startswith(("FG", "MK")):
            if manufacturing_type == "plastic" or "plastic" in category_name or "พลาสติก" in category_name:
                return "FG_PLASTIC"
            if (
                manufacturing_type == "pharma"
                or any(token in category_name for token in ("ยาดม", "พิมเสน", "pepex", "pax", "mark ii", "บาล์ม"))
            ):
                return "FG_PHARMA"
            return "OTHER_INV"

        if "/ services" in category_name:
            return "OTHER_INV"

        return "OTHER_INV"

    @api.model
    def setup_default_groups_and_assign(self, dry_run=False):
        group_map = {}
        for vals in self._default_group_definitions():
            group = self.search([("code", "=", vals["code"])], limit=1)
            if not group and not dry_run:
                group = self.create(vals)
            group_map[vals["code"]] = group

        templates = self.env["product.template"].search([])
        changed_templates = self.env["product.template"]
        summary = Counter()

        for template in templates:
            code = self._resolve_report_group_code(template)
            summary[code] += 1
            if dry_run:
                continue
            target_group = group_map.get(code)
            if target_group and template.report_group_id != target_group:
                template.report_group_id = target_group.id
                changed_templates |= template

        return {
            "message": _("Dry run completed.") if dry_run else _("Default report groups created and assigned."),
            "groups": {code: (group_map[code].id if group_map.get(code) else False) for code in group_map},
            "summary": dict(summary),
            "updated_templates": len(changed_templates),
        }
