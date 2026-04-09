from datetime import date
from calendar import month_name

from odoo import api, fields, models, _
from odoo import SUPERUSER_ID


class MBRAccountMap(models.Model):
    _name = "mbr.account.map"
    _description = "MBR Account Mapping"

    # Canonical account code mapping to MBR lines
    LINES_MAP = {
        "1.1": {"410001", "410002", "410003", "410004", "410088"},
        "1.2": {"420001", "420006", "420007", "430001"},
        "1.3": {"420002"},
        "1.4": {
            "470003",
            "470004",
            "470005",
            "420003",
            "470006",
            "470007",
            "470008",
            "420004",
            "480001",
        },
        "2.1": {"510001", "510002", "510003", "510004", "520100"},
        "2.2": {"520001", "520002", "520004", "520005"},
        "2.3": {"540014"},
        "2.4": {
            "590001",
            "590002",
            "590003",
            "590004",
            "590005",
            "590006",
            "522008",
            "530001",
            "530002",
            "530005",
            "530006",
            "530007",
            "530008",
            "530009",
            "530004",
            "540001",
            "540003",
            "540004",
            "540005",
            "540006",
            "540002",
            "610312",
            "540007",
            "540008",
            "550029",
            "550058",
            "540010",
            "522001",
            "522002",
            "522005",
            "540011",
            "550008",
            "550014",
            "550034",
            "540012",
            "621302",
        },
        "3.1": {
            "620101",
            "620102",
            "620103",
            "620104",
            "620105",
            "620106",
            "620107",
            "620108",
            "620109",
            "620110",
            "620111",
            "620113",
            "620114",
            "620115",
            "620116",
            "621109",
        },
        "3.2": {"620815"},
        "3.3": {"620501", "620502", "620503", "620504", "620506", "620508"},
        "3.4": {"620201", "620202", "620301", "620302", "620303"},
        "3.5": {"620601", "620602", "620603", "620604", "620605", "620606", "621108"},
        "3.6": {
            "610301",
            "610302",
            "610303",
            "610304",
            "610305",
            "610306",
            "610307",
            "610308",
            "610309",
            "610310",
            "610313",
            "610314",
            "610315",
            "610316",
            "610317",
            "621314",
            "610320",
        },
        "3.7": {"620112", "620813"},
        "3.8": {"620905", "620906"},
        "3.9": {"620701", "620702", "620703", "620704"},
        "3.10": {
            "621001",
            "621002",
            "621003",
            "621004",
            "621005",
            "621006",
            "621110",
            "621111",
            "621112",
            "621101",
            "550035",
            "621113",
            "621501",
        },
        "3.11": {
            "621201",
            "621202",
            "621203",
            "621204",
            "621205",
            "621206",
            "621207",
            "621208",
            "621209",
            "621210",
            "621211",
            "621212",
            "621213",
            "621214",
            "621215",
        },
        "3.12": {"610311", "550025"},
        "3.13": {
            "620401",
            "610304",
            "620402",
            "620403",
            "620404",
            "620405",
            "620406",
            "620408",
            "620802",
            "620801",
            "620803",
            "620814",
            "620903",
            "621301",
            "621303",
            "621304",
            "621305",
            "621306",
            "620505",
            "621307",
            "621308",
            "621309",
            "621312",
            "621310",
            "621311",
            "621315",
            "620304",
            "620305",
            "710002",
        },
        "3.14": {"470001", "470002"},
        "4.1": {"621402", "621405", "621404"},
        "4.2": {"621401", "621403", "620901", "620904"},
    }
    line_code = fields.Selection(
        selection=[
            ("1.1", "1.1 Sales"),
            ("1.2", "1.2 Services"),
            ("1.3", "1.3 Rental"),
            ("1.4", "1.4 Other income"),
            ("2.1", "2.1 Cost of Sales"),
            ("2.2", "2.2 Cost of Services"),
            ("2.3", "2.3 Cost of Rental"),
            ("2.4", "2.4 Other cost of revenue"),
            ("3.1", "3.1 Salary and Benefit and Other"),
            ("3.2", "3.2 Management / Technical Service fee"),
            ("3.3", "3.3 Rental expenses"),
            ("3.4", "3.4 Utilities"),
            ("3.5", "3.5 Travelling and Accommodation"),
            ("3.6", "3.6 Commission and Marketing"),
            ("3.7", "3.7 Training"),
            ("3.8", "3.8 Tax and government fee"),
            ("3.9", "3.9 Consulting fees"),
            ("3.10", "3.10 Repair and maintenance"),
            ("3.11", "3.11 Depreciations"),
            ("3.12", "3.12 Transportation expenses"),
            ("3.13", "3.13 Other expenses"),
            ("3.14", "3.14 FX Gain / Loss"),
            ("4.1", "4.1 Interest"),
            ("4.2", "4.2 Other financial costs"),
        ],
        required=True,
    )
    account_id = fields.Many2one(
        "account.account",
        string="Account",
        required=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    _sql_constraints = [
        (
            "uniq_line_account",
            "unique(line_code, account_id)",
            "Each account can be mapped to each MBR line only once.",
        )
    ]

    @api.model
    def _auto_create_default_map(self):
        """
        Create mappings from the canonical LINES_MAP.
        Always rebuild per company to ensure it matches the fixed list.
        """
        Account = self.env["account.account"]
        code_to_line = {}
        for line_code, codes in self.LINES_MAP.items():
            for code in codes:
                code_to_line[code.strip()] = line_code

        for company in self.env["res.company"].search([]):
            self.search([("company_id", "=", company.id)]).unlink()
            create_vals = []
            accounts = Account.search([("company_ids", "in", company.id)])
            for acc in accounts:
                line_code = code_to_line.get((acc.code or "").strip())
                if not line_code:
                    continue
                create_vals.append(
                    {
                        "company_id": company.id,
                        "account_id": acc.id,
                        "line_code": line_code,
                    }
                )
            if create_vals:
                self.create(create_vals)


def _mbr_post_init(cr, registry):
    """Create default mappings per company based on the fixed COA lists."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    Map = env["mbr.account.map"]
    Account = env["account.account"]

    # Exact code→line mapping provided by the user
    lines_map = {
        "1.1": {
            "410001", "410002", "410003", "410004", "410088",
        },
        "1.2": {
            "420001", "420006", "420007", "430001",
        },
        "1.3": {
            "420002",
        },
        "1.4": {
            "470003", "470004", "470005", "420003", "470006", "470007",
            "470008", "420004", "480001",
        },
        "2.1": {
            "510001", "510002", "510003", "510004", "520100",
        },
        "2.2": {
            "520001", "520002", "520004", "520005",
        },
        "2.3": {
            "540014",
        },
        "2.4": {
            "590001", "590002", "590003", "590004", "590005", "590006",
            "522008", "530001", "530002", "530005", "530006", "530007",
            "530008", "530009", "530004", "540001", "540003", "540004",
            "540005", "540006", "540002", "610312", "540007", "540008",
            "550029", "550058", "540010", "522001", "522002", "522005",
            "540011", "550008", "550014", "550034", "540012", "621302",
        },
        "3.1": {
            "620101", "620102", "620103", "620104", "620105", "620106",
            "620107", "620108", "620109", "620110", "620111", "620113",
            "620114", "620115", "620116", "621109",
        },
        "3.2": {"620815"},
        "3.3": {"620501", "620502", "620503", "620504", "620506", "620508"},
        "3.4": {"620201", "620202", "620301", "620302", "620303"},
        "3.5": {
            "620601", "620602", "620603", "620604", "620605", "620606", "621108",
        },
        "3.6": {
            "610301", "610302", "610303", "610304", "610305", "610306",
            "610307", "610308", "610309", "610310", "610313", "610314",
            "610315", "610316", "610317", "621314", "610320",
        },
        "3.7": {"620112", "620813"},
        "3.8": {"620905", "620906"},
        "3.9": {"620701", "620702", "620703", "620704"},
        "3.10": {
            "621001", "621002", "621003", "621004", "621005", "621006",
            "621110", "621111", "621112", "621101", "550035", "621113",
            "621501",
        },
        "3.11": {
            "621201", "621202", "621203", "621204", "621205", "621206",
            "621207", "621208", "621209", "621210", "621211", "621212",
            "621213", "621214", "621215",
        },
        "3.12": {"610311", "550025"},
        "3.13": {
            "620401", "610304", "620402", "620403", "620404", "620405",
            "620406", "620408", "620802", "620801", "620803", "620814",
            "620903", "621301", "621303", "621304", "621305", "621306",
            "620505", "621307", "621308", "621309", "621312", "621310",
            "621311", "621315", "620304", "620305", "710002",
        },
        "3.14": {"470001", "470002"},
        "4.1": {"621402", "621405", "621404"},
        "4.2": {"621401", "621403", "620901", "620904"},
    }

    code_to_line = {}
    for line_code, codes in lines_map.items():
        for code in codes:
            code_to_line[code.strip()] = line_code

    for company in env["res.company"].search([]):
        # Always rebuild to match the canonical list exactly.
        Map.search([("company_id", "=", company.id)]).unlink()
        create_vals = []
        accounts = Account.search([("company_ids", "in", company.id)])
        for acc in accounts:
            line_code = code_to_line.get((acc.code or "").strip())
            if not line_code:
                continue
            create_vals.append(
                {
                    "company_id": company.id,
                    "account_id": acc.id,
                    "line_code": line_code,
                }
            )
        if create_vals:
            Map.create(create_vals)
