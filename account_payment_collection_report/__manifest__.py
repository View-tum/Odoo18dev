{
    "name": "Account: Payment Collection Report",
    "version": "18.0.2.0.0",
    "summary": "Jasper Payment Collection Report with advanced filtering by Route or Customer.",
    "description": """ 
        Payment Collection Report Wizard (Jasper)
        =========================================
        Generate comprehensive payment collection reports via Jasper with flexible filtering.

        **Key Features:**
        * **Smart Filtering:** Filter by Delivery Route (including sub-regions) or specific Customers.
        * **Auto Date Range:** Defaults to the current business day (starts at 08:00 AM).
        * **Status Control:** Option to filter only "Unprinted" documents to prevent duplicates.
        * **Jasper Integration:** Seamlessly passes parameters to the Jasper Reporting engine.
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
    ],
    "data": [
        "security/ir.model.access.csv",
        "report/account_payment_collection_report_view.xml",
        "views/account_menuitem.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "account_payment_collection_report/static/src/css/notification_style.css",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
