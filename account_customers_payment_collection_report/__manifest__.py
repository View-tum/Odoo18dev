{
    "name": "Accounting Customer Payment Collection Report",
    "version": "18.0.1.0.1",
    "summary": "Accounting Customer Invoice Payment Collection Report",
    "description": """
    This module provides a report for customer invoice payments in the accounting module.
    """,
    "author": "K.",
    "website": "https://www.365infotech.co.th/",
    "license": "LGPL-3",
    "depends": [
        "base",
        "sale",
        "sale_management",
        "sales_team",
        "account",
        "account_payment_collection_report",
        "oi_jasper_report",
    ],
    "data": [
        "security/ir.model.access.csv",
        "report/account_customers_payment_collection_report_view.xml",
        "views/account_menuitem.xml",
    ],
    "assets": {},
    "installable": True,
    "application": False,
    "auto_install": False,
}
