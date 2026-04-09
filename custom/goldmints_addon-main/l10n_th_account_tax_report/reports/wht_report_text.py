# Copyright 2025 Ecosoft Co., Ltd (https://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import re
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from odoo import models
from odoo.exceptions import UserError


class WithholdingTaxReportText(models.AbstractModel):
    _name = "report.l10n_th_account_tax_report.report_withholding_tax_text"
    _inherit = [
        "report.l10n_th_account_tax_report.report_withholding_tax",
        "thai.utils",
    ]
    _description = "Thai Withholding Tax Report Text"

    _RD_FORBIDDEN_CHARS = re.compile(r"[\|\r\n\*+/\\\\!$%#&@,'\"]")

    def _convert_wht_tax_payer(self, tax_payer):
        if tax_payer == "withholding":
            return 1
        if tax_payer == "paid_continue":
            return 2
        return 3  # Paid One Time

    def _prepare_display_wht_textfile(self, record, prefix=""):
        args = defaultdict(str)
        for field in record:
            key = f"{prefix}{field}" if prefix else field
            if field == "cert_date":
                args[key] = self.format_thai_date(
                    record[field],
                    month_format="numeric",
                    format_date="{day:02d}{month}{year}",
                )
            elif field in ["base", "amount"]:
                args[key] = f"{record[field]:,.2f}"
            elif field == "cert_tax_payer":
                args[key] = self._convert_wht_tax_payer(record[field])
            elif field == "wht_percent":
                args[key] = int(record[field])
            else:
                args[key] = record[field] or ""
        return args

    def _extract_fields_from_template(self, wht_textfile_format):
        return re.findall(r"%\((.*?)\)s", wht_textfile_format)

    def _get_wht_group_cert(self, wht_report_data):
        grouped = defaultdict(list)
        wht_groupby_cert = []

        for row in wht_report_data:
            grouped[row["cert_id"]].append(row)

        for idx, (cert_id, rows) in enumerate(grouped.items(), start=1):
            first_row = rows[0]
            cert_cancel = first_row["cert_cancel"]

            wht_groupby_cert.append(
                {
                    # Header
                    "row_number": idx,
                    "cert_cancel": cert_cancel,
                    "cert_date": first_row["cert_date"],
                    "cert_date_str": first_row["cert_date_str"],
                    "cert_name": first_row["cert_name"],
                    "cert_tax_payer": first_row["cert_tax_payer"],
                    "cert_tax_payer_display": first_row["cert_tax_payer_display"],
                    "cert_tax_payer_code": first_row["cert_tax_payer_code"],
                    "partner_id": first_row["partner_id"],
                    "partner_name": first_row["partner_name"],
                    "partner_title": first_row["partner_title"],
                    "partner_firstname": first_row["partner_firstname"],
                    "partner_lastname": first_row["partner_lastname"],
                    "partner_address": first_row["partner_address"],
                    "partner_street": first_row["partner_street"],
                    "partner_street2": first_row["partner_street2"],
                    "partner_city": first_row["partner_city"],
                    "partner_state": first_row["partner_state"],
                    "partner_zip": first_row["partner_zip"],
                    "partner_country": first_row["partner_country"],
                    "partner_vat": first_row["partner_vat"],
                    "partner_branch": first_row["partner_branch"],
                    "partner_bank_account": first_row["partner_bank_account"],
                    "cert_id": cert_id,
                    # Lines
                    "lines": rows,
                }
            )
        return wht_groupby_cert

    def _text_wht_pnd1(self, report_values, wht_textfile_format):
        wht_code_income = self.env["withholding.tax.code.income"]
        text = ""
        for line in report_values["wht_report_data"]:
            if line["wht_cert_income_code"]:
                wht_code_income = wht_code_income.browse(
                    line["wht_cert_income_code"][0]
                )
            args = defaultdict(str, {"income_code": wht_code_income.code or ""})
            for field in line:
                if field == "cert_date":
                    args[field] = self.format_thai_date(
                        line[field],
                        month_format="numeric",
                        format_date="{day:02d}{month}{year}",
                    )
                elif field in ["base", "amount"]:
                    args[field] = f"{line[field]:,.2f}"
                elif field == "cert_tax_payer":
                    args[field] = self._convert_wht_tax_payer(line[field])
                elif field == "wht_percent":
                    args[field] = int(line[field])
                else:
                    args[field] = line[field] or ""

            text += wht_textfile_format % args
        return text

    def _create_text_wht(self, report_values, wht_textfile_format):
        text = ""
        # NOTE: PND1 support 1 line only
        if report_values["income_tax_form"] == "pnd1":
            text = self._text_wht_pnd1(report_values, wht_textfile_format)
            return text

        wht_groupby_cert = self._get_wht_group_cert(report_values["wht_report_data"])
        loop_fields = [
            f
            for f in self._extract_fields_from_template(wht_textfile_format)
            if f.startswith("loop_")
        ]

        max_lines = (
            max(len(cert["lines"]) for cert in wht_groupby_cert)
            if wht_groupby_cert
            else 0
        )
        for cert in wht_groupby_cert:
            args = self._prepare_display_wht_textfile(cert)

            if loop_fields:
                loop_parts = []
                for i in range(max_lines):
                    if i < len(cert["lines"]):
                        line_args = self._prepare_display_wht_textfile(
                            cert["lines"][i], prefix="loop_"
                        )
                        loop_parts.append(
                            "".join([f"|{line_args[f]}" for f in loop_fields])
                        )
                    else:
                        loop_parts.append("".join(["|" for _ in loop_fields]))

                args["__loop__"] = "".join(loop_parts)

                wht_textfile_format = wht_textfile_format.replace(
                    "|".join([f"%({f})s" for f in loop_fields]),
                    "%(__loop__)s",
                )

            text += wht_textfile_format % args
        return text

    def _rd_digits(self, value):
        return re.sub(r"\D", "", value or "")

    def _rd_bool(self, value):
        return "1" if value else "0"

    def _rd_amount(self, value):
        amount = Decimal(str(value or 0)).quantize(Decimal("0.01"), ROUND_HALF_UP)
        return f"{amount:.2f}"

    def _rd_clean_text(self, value, field_name, max_length, required=False):
        text = (value or "").strip()
        text = self._RD_FORBIDDEN_CHARS.sub(" ", text)
        text = re.sub(r"\s+", " ", text).strip()
        if required and not text:
            raise UserError(self.env._("%s is required for RD V2 export.") % field_name)
        if len(text) > max_length:
            raise UserError(
                self.env._("%s exceeds maximum length %s for RD V2 export.")
                % (field_name, max_length)
            )
        return text

    def _rd_branch(self, value, field_name):
        digits = self._rd_digits(value)
        if not digits:
            return "000000"
        if len(digits) > 6:
            raise UserError(
                self.env._("%s must not exceed 6 digits for RD V2 export.")
                % field_name
            )
        return digits.zfill(6)

    def _rd_tax_id(self, value, field_name, length=13, required=True):
        digits = self._rd_digits(value)
        if not digits:
            if required:
                raise UserError(
                    self.env._("%s is required for RD V2 export.") % field_name
                )
            return ""
        if len(digits) != length:
            raise UserError(
                self.env._("%s must contain exactly %s digits for RD V2 export.")
                % (field_name, length)
            )
        return digits

    def _rd_date(self, value, zero_if_empty=False):
        if not value:
            return "00000000" if zero_if_empty else ""
        return self.format_thai_date(
            value,
            month_format="numeric",
            format_date="{day:02d}{month}{year}",
        )

    def _rd_company_branch(self, company):
        partner = company.partner_id
        branch = getattr(partner, "branch", False) or partner.company_registry or ""
        return self._rd_branch(branch, "Company branch")

    def _rd_company_tax_id(self, company):
        return self._rd_tax_id(company.partner_id.vat, "Company tax ID")

    def _rd_sender_values(self, data, company):
        return {
            "sender_id": self._rd_clean_text(
                data.get("rd_sender_id"), "RD sender ID", 4, required=True
            ),
            "sender_nid": self._rd_tax_id(
                data.get("rd_sender_nid"), "RD sender tax ID"
            ),
            "sender_branch": self._rd_branch(
                data.get("rd_sender_branch"), "RD sender branch"
            ),
            "sender_role": self._rd_clean_text(
                data.get("rd_sender_role"), "RD sender role", 1, required=True
            ),
            "dept_name": self._rd_clean_text(
                data.get("rd_dept_name"), "RD department name", 80, required=True
            ),
            "lto": self._rd_bool(data.get("rd_lto")),
            "branch_type": self._rd_clean_text(
                data.get("rd_branch_type"), "RD branch type", 1
            ),
            "form_type": self._rd_clean_text(
                (data.get("rd_form_type") or "00").zfill(2),
                "RD form type",
                2,
                required=True,
            ),
            "submission_seq": self._rd_clean_text(
                (data.get("rd_submission_seq") or "00").zfill(2),
                "RD submission sequence",
                2,
                required=True,
            ),
            "form_flag": self._rd_clean_text(
                data.get("rd_form_flag"), "RD form flag", 1, required=True
            ),
            "user_id": self._rd_clean_text(
                data.get("rd_user_id"), "RD user ID", 20, required=True
            ),
            "sur_amt": self._rd_amount(data.get("rd_sur_amt")),
            "trans_amt": self._rd_amount(data.get("rd_trans_amt")),
            "company_nid": self._rd_company_tax_id(company),
            "company_branch": self._rd_company_branch(company),
            "tax_month": f"{data['date_from'].month:02d}",
            "tax_year": str(data["date_from"].year + 543),
        }

    def _rd_partner_name_parts(self, partner):
        title = ""
        if partner.company_type == "company":
            title = (
                getattr(partner.partner_company_type_id, "prefix", False)
                or partner.title.name
                or ""
            )
            first_name = partner.name_company or partner.name or ""
            last_name = ""
        else:
            title = partner.title.name or ""
            first_name = getattr(partner, "firstname", False) or partner.name or ""
            last_name = getattr(partner, "lastname", False) or ""
        return {
            "title_name": self._rd_clean_text(title, "Partner title", 100),
            "first_name": self._rd_clean_text(
                first_name, "Partner first name", 100, required=True
            ),
            "last_name": self._rd_clean_text(last_name, "Partner last name", 80),
        }

    def _rd_partner_address_parts(self, partner):
        return {
            "build_name": self._rd_clean_text("", "Building name", 40),
            "room_no": self._rd_clean_text("", "Room number", 20),
            "floor_no": self._rd_clean_text("", "Floor number", 20),
            "village_name": self._rd_clean_text("", "Village name", 80),
            "add_no": self._rd_clean_text(partner.street or "", "Address number", 20),
            "moo_no": self._rd_clean_text("", "Moo number", 20),
            "soi": self._rd_clean_text("", "Soi", 80),
            "street_name": self._rd_clean_text("", "Street", 80),
            "tambon": self._rd_clean_text(partner.street2 or "", "Tambon", 80),
            "amphur": self._rd_clean_text(partner.city or "", "Amphur", 80),
            "province": self._rd_clean_text(
                partner.state_id.name or "", "Province", 80
            ),
            "postal_code": self._rd_clean_text(partner.zip or "", "Postal code", 5),
        }

    def _rd_group_lines_by_cert(self, report_values):
        return self._get_wht_group_cert(report_values["wht_report_data"])

    def _rd_chunk(self, items, size=3):
        for idx in range(0, len(items), size):
            yield items[idx : idx + size]

    def _rd_validate_wizard_options(self, report_values, data):
        if report_values["show_cancel"]:
            raise UserError(
                self.env._(
                    "RD V2 TXT export does not allow 'Show Cancelled'. Untick it and export again."
                )
            )
        if data["date_from"].year != data["date_to"].year or data["date_from"].month != data["date_to"].month:
            raise UserError(
                self.env._(
                    "RD V2 TXT export requires Date From and Date To to be in the same month."
                )
            )

    def _rd_header_fields(self, tax_type, data, company, detail_records, section_fields):
        rd = self._rd_sender_values(data, company)
        total_base = sum(Decimal(rec["tot_base"]) for rec in detail_records)
        total_tax = sum(Decimal(rec["tot_tax"]) for rec in detail_records)
        sur_amt = Decimal(rd["sur_amt"])
        header = [
            "H",
            rd["sender_id"],
            rd["sender_nid"],
            rd["sender_branch"],
            rd["sender_role"],
            tax_type,
            rd["company_nid"],
            rd["company_branch"],
            rd["dept_name"],
            *section_fields,
            rd["lto"],
            rd["tax_month"],
            rd["tax_year"],
            rd["branch_type"],
            rd["form_type"],
            str(len(detail_records)),
            self._rd_amount(total_base),
            self._rd_amount(total_tax),
            rd["sur_amt"],
            self._rd_amount(total_tax + sur_amt),
            rd["trans_amt"],
            rd["user_id"],
            rd["form_flag"],
        ]
        return header

    def _rd_detail_line_sets(self, cert_lines):
        line_sets = []
        for line in cert_lines:
            line_sets.append(
                [
                    self._rd_date(line["cert_date"]),
                    self._rd_amount(line["wht_percent"]),
                    self._rd_amount(line["base"]),
                    self._rd_amount(line["amount"]),
                    self._rd_clean_text(
                        line["wht_cert_income_desc"] or "",
                        "WHT income description",
                        100,
                    ),
                    str(line["cert_tax_payer_code"]),
                ]
            )
        while len(line_sets) < 3:
            line_sets.append(
                ["00000000", "0.00", "0.00", "0.00", "", ""]
            )
        return line_sets[:3]

    def _rd_detail_record(self, seq_no, cert, cert_lines, company, tax_type):
        partner = self.env["res.partner"].browse(cert["partner_id"])
        partner_name = self._rd_partner_name_parts(partner)
        partner_address = self._rd_partner_address_parts(partner)
        payer_tax_id = self._rd_tax_id(partner.vat, "Payee tax ID")
        detail_tax_id = "0000000000"
        line_sets = self._rd_detail_line_sets(cert_lines)
        fields = [
            "D",
            str(seq_no),
            self._rd_company_branch(company),
            payer_tax_id,
            detail_tax_id,
            partner_name["title_name"],
            partner_name["first_name"],
            partner_name["last_name"],
        ]
        for line_set in line_sets:
            fields.extend(line_set)
        fields.extend(
            [
                partner_address["build_name"],
                partner_address["room_no"],
                partner_address["floor_no"],
                partner_address["village_name"],
                partner_address["add_no"],
                partner_address["moo_no"],
                partner_address["soi"],
                partner_address["street_name"],
                partner_address["tambon"],
                partner_address["amphur"],
                partner_address["province"],
                partner_address["postal_code"],
            ]
        )
        return {
            "fields": fields,
            "tot_base": sum(Decimal(str(line["base"])) for line in cert_lines),
            "tot_tax": sum(Decimal(str(line["amount"])) for line in cert_lines),
            "tax_type": tax_type,
        }

    def _rd_build_detail_records(self, report_values, company, tax_type):
        detail_records = []
        seq_no = 1
        for cert in self._rd_group_lines_by_cert(report_values):
            for cert_lines in self._rd_chunk(cert["lines"], size=3):
                detail_records.append(
                    self._rd_detail_record(seq_no, cert, cert_lines, company, tax_type)
                )
                seq_no += 1
        return detail_records

    def _rd_section_fields(self, income_tax_form, data):
        if income_tax_form == "pnd53":
            return [
                self._rd_bool(data.get("rd_section3")),
                self._rd_bool(data.get("rd_section65")),
                self._rd_bool(data.get("rd_section69")),
            ]
        return [
            self._rd_bool(data.get("rd_section3")),
            self._rd_bool(data.get("rd_section48")),
            self._rd_bool(data.get("rd_section50")),
        ]

    def _create_rd_v2_text_wht(self, report_values):
        data = report_values["docs"]._prepare_report_wht()
        company = self.env["res.company"].browse(data["company_id"])
        self._rd_validate_wizard_options(report_values, data)
        tax_type = report_values["income_tax_form"].upper()
        detail_records = self._rd_build_detail_records(report_values, company, tax_type)
        section_fields = self._rd_section_fields(report_values["income_tax_form"], data)
        header_fields = self._rd_header_fields(
            tax_type, data, company, detail_records, section_fields
        )
        lines = ["|".join(header_fields)]
        lines.extend("|".join(detail["fields"]) for detail in detail_records)
        return "\r\n".join(lines)

    def _get_report_values(self, docids, data):
        report_values = super()._get_report_values(docids, data)
        data = report_values["docs"]._prepare_report_wht()

        company = self.env["res.company"].browse(data["company_id"])

        if (
            company.wht_report_format == "rd"
            and report_values["income_tax_form"] in ("pnd3", "pnd53")
        ):
            report_values["text_file_value"] = self._create_rd_v2_text_wht(
                report_values
            )
            return report_values

        try:
            wht_textfile_format = company[
                f"wht_text_file_{report_values['income_tax_form']}_format"
            ]
        except Exception as e:
            raise UserError(
                f"Not implement {report_values['income_tax_form']} yet"
            ) from e

        text_file_value = self._create_text_wht(report_values, wht_textfile_format)
        report_values["text_file_value"] = text_file_value
        return report_values
