# -*- coding: utf-8 -*-
{
    "name": "Account: Aged Receiveable Extension",
    "summary": "Aged Receivable Report with Due Date and Payment Terms",
    "description": """
        This module extends the standard Aged Receivable report to include due dates and payment terms.
    """,
    "author": "365 infotech",
    "website": "https://www.365infotech.co.th/",
    "category": "Accounting/Accounting",
    "version": "18.0.1.1.0",
    "depends": [
        "base",
        "account",
        "sale",
        "sale_management",
        "sales_team",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizard/account_aged_receiveable_extension_view.xml",
        "views/account_menuitem.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    "auto_install": False,
}
