{
    "name": "Account: Expense Report",
    "version": "18.0.1.0.0",
    "summary": "Accounting module to manage expense reports",
    "author": "365 infotech",
    "website": "https://www.365infotech.co.th/",
    "category": "Accounting",
    "license": "LGPL-3",
    "depends": [
        "base",
        "product",
        "account",
        "account_payment_collection_report",
        "oi_jasper_report",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizard/expense_report_wizard_view.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
