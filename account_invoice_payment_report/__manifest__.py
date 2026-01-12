{
    "name": "Account: Invoice Payment Report",
    "version": "18.0.1.0.0",
    "summary": "Wizard to generate Invoice Payment Reports via Jasper.",
    "description": """
        Provides a wizard to print Invoice Payment Reports.
        Allows filtering by Salesperson and Date Range.
    """,
    "author": "365 infotech",
    "website": "https://www.365infotech.co.th/",
    "license": "LGPL-3",
    "depends": [
        "account",
        "account_payment_collection_report",
        "base",
        "oi_jasper_report",
        "sale",
        "sale_management",
        "sales_team",
    ],
    "data": [
        "security/ir.model.access.csv",
        "report/account_invoice_payment_report_view.xml",
        "views/account_menuitem.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "account_invoice_payment_report/static/src/css/notification_style.css",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
