# __manifest__.py
{
    "name": "Account: Lot Traceability",
    "summary": "Trace Invoice from Stock Lot/Serial Number",
    "description": """
        This module allows users to trace invoices back to their associated stock lots or serial numbers.
    """,
    "author": "365 infotech",
    "website": "https://www.365infotech.co.th/",
    "category": "Accounting",
    "version": "18.0.1.0.0",
    "depends": ["account", "stock", "sale_management"],
    "data": [
        "security/ir.model.access.csv",
        "wizard/account_lot_traceability_views.xml",
        "views/account_menuitem.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    "auto_install": False,
}
