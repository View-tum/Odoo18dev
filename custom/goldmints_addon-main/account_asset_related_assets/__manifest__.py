{
    "name": "Account Asset Related Assets Alert",
    "version": "18.0.1.0.0",
    "summary": "Link assets together and warn before deleting or selling a linked asset.",
    "description": """
Allow users to relate assets to each other. If a linked asset is deleted or removed/sold, the user sees an alert listing the other related assets.
    """,
    "category": "Accounting",
    "author": "Phyo Thet Paing/paingphyothet561@gmail.com",
    "website": "https://www.365infotech.co.th/",
    "license": "LGPL-3",
    "depends": [
        "account_asset",
        "sale",
    ],
    "data": [
        "views/account_asset_views.xml",
        "views/account_asset_hierarchy_views.xml",
    ],
    "installable": True,
    "application": False,
}
