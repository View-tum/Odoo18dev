# -*- coding: utf-8 -*-
{
    "name": "Account Asset Customization",
    "summary": "Improves asset tracking, reporting, and accounting integration.",
    "description": """
Extend asset handling with extra fields and account control:
- Adds responsible user and asset location on the asset form.
- Extends asset account domain/context to include prepayment asset accounts.
    """,
    "version": "1.0.0",
    "category": "Accounting/ Assets",
    "author": "Phyo Thet Paing/paingphyothet561@gmail.com",
    "website": "https://www.365infotech.co.th/",
    "license": "LGPL-3",
    "depends": [
        "base",
        "account_asset",
        "analytic",
    ],
    "data": [
        "views/account_asset_view.xml",
        "views/account_analytic_plan_view.xml",
    ],
    "installable": True,
    "application": False,
}
