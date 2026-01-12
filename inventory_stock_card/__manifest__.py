# -*- coding: utf-8 -*-
{
    "name": "Inventory: Stock Card",
    "summary": "Stock Card Report for Inventory Movements",
    "version": "18.0.1.0.0",
    "category": "Inventory/Reporting",
    "author": "365 infotech",
    "license": "LGPL-3",
    "website": "https://www.365infotech.co.th/",
    "depends": [
        "stock",
        "product",
        "web",
        "base"],
    "data": [
        "security/ir.model.access.csv",
        "views/inventory_stock_card_action.xml",
        "wizards/inventory_stock_card_wizard_views.xml",
        "report/inventory_stock_card_report_views.xml",
    ],
    "assets": {
        "web.report_assets_common": [
            "inventory_stock_card/static/src/scss/inventory_stock_card_report.scss",
        ],
    },
    "installable": True,
    "application": False,
}
