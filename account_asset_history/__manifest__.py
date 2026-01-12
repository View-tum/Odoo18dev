# -*- coding: utf-8 -*-
{
    "name": "Account: Asset Modify History",
    "summary": "Track modification history of assets",
    "version": "18.0.1.0.0",
    "author": "365 infotech",
    "website": "https://www.365infotech.com",
    "category": "Accounting/Assets",
    "depends": [
        "base",
        "account",
        "account_asset",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/asset_history_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}
