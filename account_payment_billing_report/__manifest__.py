{
    "name": "Account: Payment Billing Report",
    "version": "18.0.1.0.0",
    "summary": "Wizard to generate Payment Billing Reports via Jasper.",
    "description": """
        Provides a wizard to print Payment Billing Reports.
        Allows filtering by Sales Region, Salesperson, and Date Range.
    """,
    "author": "365 infotech",
    "website": "https://www.365infotech.co.th/",
    "category": "Accounting",
    "license": "LGPL-3",
    "depends": [
        "base",
        "account",
        "delivery_routes_management",
        "delivery_pickup_transport",
        "oi_jasper_report",
        "account_payment_collection_report",
        "sale",
        "sale_management",
        "sales_team",
    ],
    "data": [
        "security/ir.model.access.csv",
        "report/account_payment_billing_report_view.xml",
        "views/account_menuitem.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "account_payment_billing_report/static/src/css/notification_style.css",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
