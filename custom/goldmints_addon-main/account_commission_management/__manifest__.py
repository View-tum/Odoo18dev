{
    "name": "Account: Commission Management",
    "summary": "Management and reporting of sales commissions for accounting.",
    "version": "18.0.1.0.0",
    "author": "365 infotech",
    "website": "https://www.365infotech.co.th/",
    "category": "Accounting",
    "license": "AGPL-3",
    "depends": [
        "base",
        "account",
        "sale",
        "sale_management",
        "sale_analysis_report",
        "delivery_routes_management",
        "account_payment_collection_report",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/account_commission_management_views.xml",
        "views/account_commission_rule_view.xml",
        "views/account_commission_rate_view.xml",
        # "views/account_commission_timestamp_view.xml",
        "views/account_menuitem.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "account_commission_management/static/src/css/notification_style.css",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
