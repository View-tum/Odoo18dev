{
    "name": "Accounting Fixed Asset Report",
    "version": "18.0.1.0.0",
    "summary": "Accounting Fixed Asset Report",
    "author": "K.",
    "website": "https://www.365infotech.co.th/",
    "license": "LGPL-3",
    "depends": [
        "account",
        "account_asset",
        "account_payment_collection_report",
        "analytic",
        "oi_jasper_report",
    ],
    "data": [
        "security/ir.model.access.csv",
        "report/account_fixed_asset_report_view.xml",
        "views/account_menuitem.xml",
    ],
    "assets": {},
    "installable": True,
    "application": False,
    "auto_install": False,
}
