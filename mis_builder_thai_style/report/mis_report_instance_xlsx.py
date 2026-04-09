# mis_builder_thai_style/report/mis_report_instance_xlsx.py
import logging
from collections import defaultdict
from datetime import datetime
import numbers

from odoo import fields, models

from odoo.addons.mis_builder.models.accounting_none import AccountingNone
from odoo.addons.mis_builder.models.data_error import DataError
from odoo.addons.mis_builder.models.mis_report_style import TYPE_STR

_logger = logging.getLogger(__name__)

ROW_HEIGHT = 15
COL_WIDTH = 1.2
MIN_COL_WIDTH = 10
MAX_COL_WIDTH = 50


class MisBuilderXlsx(models.AbstractModel):
    _inherit = "report.mis_builder.mis_report_instance_xlsx"

    def generate_xlsx_report(self, workbook, data, objects):

        matrix = objects._compute_matrix()
        style_obj = self.env["mis.report.style"]

        report_name = "{} - {}".format(
            objects[0].name, ", ".join([a.name for a in objects[0].query_company_ids])
        )
        sheet = workbook.add_worksheet(report_name[:31])
        row_pos = 0
        col_pos = 0
        label_col_width = MIN_COL_WIDTH
        col_width = defaultdict(lambda: MIN_COL_WIDTH)

        bold = workbook.add_format(
            {
                "bold": True,
                "font_name": "Angsana New",
                "font_size": 20,
            }
        )

        header_format = workbook.add_format(
            {
                "bold": True,
                "align": "center",
                "bg_color": "#F0EEEE",
                "font_name": "Angsana New",
                "font_size": 16,
                "valign": "vcenter",
            }
        )

        sheet.write(row_pos, 0, report_name, bold)
        row_pos += 2

        filter_descriptions = objects.get_filter_descriptions()
        if filter_descriptions:
            for filter_description in objects.get_filter_descriptions():
                sheet.write(row_pos, 0, filter_description, bold)
                row_pos += 1
            row_pos += 1

        sheet.write(row_pos, 0, "", header_format)
        col_pos = 1
        for col in matrix.iter_cols():
            label = col.label
            if col.description:
                label += "\n" + col.description
                sheet.set_row(row_pos, ROW_HEIGHT * 2)
            if col.colspan > 1:
                sheet.merge_range(
                    row_pos,
                    col_pos,
                    row_pos,
                    col_pos + col.colspan - 1,
                    label,
                    header_format,
                )
            else:
                sheet.write(row_pos, col_pos, label, header_format)
                col_width[col_pos] = max(
                    col_width[col_pos], len(col.label or ""), len(col.description or "")
                )
            col_pos += col.colspan
        row_pos += 1

        sheet.write(row_pos, 0, "", header_format)
        col_pos = 1
        for subcol in matrix.iter_subcols():
            label = subcol.label
            if subcol.description:
                label += "\n" + subcol.description
                sheet.set_row(row_pos, ROW_HEIGHT * 2)
            sheet.write(row_pos, col_pos, label, header_format)
            col_width[col_pos] = max(
                col_width[col_pos],
                len(subcol.label or ""),
                len(subcol.description or ""),
            )
            col_pos += 1
        row_pos += 1

        for row in matrix.iter_rows():
            if (
                row.style_props.hide_empty and row.is_empty()
            ) or row.style_props.hide_always:
                continue

            row_xlsx_style = style_obj.to_xlsx_style(TYPE_STR, row.style_props)
            row_format = workbook.add_format(row_xlsx_style)

            col_pos = 0
            label = row.label
            if row.description:
                label += "\n" + row.description
                sheet.set_row(row_pos, ROW_HEIGHT * 2)
            sheet.write(row_pos, col_pos, label, row_format)
            label_col_width = max(
                label_col_width, len(row.label or ""), len(row.description or "")
            )
            for cell in row.iter_cells():
                col_pos += 1
                if not cell or cell.val is AccountingNone:
                    sheet.write(row_pos, col_pos, "", row_format)
                    continue

                cell_xlsx_style = style_obj.to_xlsx_style(
                    cell.val_type, cell.style_props, no_indent=True
                )
                cell_xlsx_style["align"] = "right"
                cell_format = workbook.add_format(cell_xlsx_style)

                if isinstance(cell.val, DataError):
                    val = cell.val.name
                elif cell.val is None or cell.val is AccountingNone:
                    val = ""
                else:
                    divider = float(cell.style_props.get("divider", 1))
                    if (
                        divider != 1
                        and isinstance(cell.val, numbers.Number)
                        and not cell.val_type == "pct"
                    ):
                        val = cell.val / divider
                    else:
                        val = cell.val
                sheet.write(row_pos, col_pos, val, cell_format)
                col_width[col_pos] = max(
                    col_width[col_pos], len(cell.val_rendered or "")
                )
            row_pos += 1

        row_pos += 1

        # Footer Create generated datetime to printing can uncomment for used

        # footer_format = workbook.add_format(
        #     {
        #         "italic": True,
        #         "font_color": "#202020",
        #         "font_size": 12,
        #         "font_name": "Angsana New",
        #     }
        # )

        # lang_model = self.env["res.lang"]
        # lang = lang_model._lang_get(self.env.user.lang)

        # now_tz = fields.Datetime.context_timestamp(
        #     self.env["res.users"], datetime.now()
        # )
        # create_date = self.env._(
        #     "Generated on %(gen_date)s at %(gen_time)s",
        #     gen_date=now_tz.strftime(lang.date_format),
        #     gen_time=now_tz.strftime(lang.time_format),
        # )
        # sheet.write(row_pos, 0, create_date, footer_format)

        sheet.set_column(0, 0, min(label_col_width, MAX_COL_WIDTH) * COL_WIDTH)
        data_col_width = min(MAX_COL_WIDTH, max(col_width.values())) + 3
        min_col_pos = min(col_width.keys())
        max_col_pos = max(col_width.keys())
        sheet.set_column(min_col_pos, max_col_pos, data_col_width * COL_WIDTH)
