# -*- coding: utf-8 -*-
{
    "name": "Inventory: Expired Products Report",
    "summary": "inventory_expired_products_report",
    "version": "18.0.1.0.2",
    "category": "Inventory/Inventory",
    "author": "365 infotech",
    "website": "https://www.365infotech.co.th/",
    "license": "LGPL-3",
    "depends": [
        "stock",
        "product",
        "oi_jasper_report",
        "report_xlsx",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/stock_menu_views.xml",
        "report/expired_products_report_view.xml",
        "report/expired_products_report_xlsx.xml",
    ],
    "assets": {},
    "installable": True,
    "application": False,
    "auto_install": False,
}
