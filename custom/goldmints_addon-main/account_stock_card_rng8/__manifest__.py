# -*- coding: utf-8 -*-
{
    "name": "Account: Stock Card RNG8",
    "summary": "Export Stock Card Balance (RNG8) to Excel Format",
    "author": "365 infotech",
    "website": "https://www.365infotech.co.th/",
    "category": "Inventory/Reporting",
    "version": "18.0.1.0.0",
    "depends": [
        "base",
        "account_payment_collection_report",
        "stock",
        "product",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/account_menu_views.xml",
        "report/account_stock_card_rng8_view.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "account_stock_card_rng8/static/src/css/notification_style.css",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}
