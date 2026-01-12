# -*- coding: utf-8 -*-
{
    "name": "Account: Invoice Payment Status",
    "summary": "View invoice statuses and bank statement dates by customer",
    "description": """
        Wizard to filter invoices by customer and date range, showing payment status and reconciled bank statement dates.
    """,
    "author": "365 infotech",
    "website": "https://www.365infotech.co.th/",
    "category": "Accounting/Accounting",
    "version": "18.0.1.0.0",
    "depends": [
        "account",
        "oi_bank_reconciliation",
        "oi_jasper_report",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizard/account_invoice_payment_status_view.xml",
        "views/account_menus.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    "auto_install": False,
}
