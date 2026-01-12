from odoo import api, models
from odoo.addons.mis_builder.models.accounting_none import AccountingNone
from odoo.addons.mis_builder.models.mis_report_style import TYPE_NUM, TYPE_STR


class MisReportStyle(models.Model):
    _inherit = "mis.report.style"

    @api.model
    def render_num(
        self, lang, value, divider=1.0, dp=0, prefix=None, suffix=None, sign="-"
    ):
        """Override: เปลี่ยนการแสดงผลหน้าเว็บ/PDF (ลบเป็นวงเล็บ)"""
        if value is None or value is AccountingNone:
            return ""

        value = round(value / float(divider or 1), dp or 0) or 0
        is_negative = value < 0

        r = lang.format("%%%s.%df" % (sign, dp or 0), abs(value), grouping=True)
        r = r.replace("-", "\N{NON-BREAKING HYPHEN}")

        if prefix:
            r = prefix + "\N{NO-BREAK SPACE}" + r
        if suffix:
            r = r + "\N{NO-BREAK SPACE}" + suffix

        if is_negative:
            r = "(" + r + ")"

        return r

    @api.model
    def to_xlsx_style(self, var_type, props, no_indent=False):
        style_dict = super(MisReportStyle, self).to_xlsx_style(
            var_type, props, no_indent
        )

        style_dict["font_name"] = "Angsana New"
        current_size = style_dict.get("font_size", 11)
        style_dict["font_size"] = current_size + 5

        if var_type == TYPE_NUM:
            base_fmt = "#,##0"
            if props.dp:
                base_fmt += "." + ("0" * props.dp)

            pos_fmt = (
                f'"{props.prefix or ""}" {base_fmt} "{props.suffix or ""}"'.strip()
            )
            neg_fmt = (
                f'"{props.prefix or ""}" ({base_fmt}) "{props.suffix or ""}"'.strip()
            )

            style_dict["num_format"] = f"{pos_fmt};{neg_fmt}"

        elif var_type == TYPE_STR:
            style_dict.pop("num_format", None)

        return style_dict
