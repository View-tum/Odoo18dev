# -*- coding: utf-8 -*-
{
    "name": "PO Asset Discount Apportionment",
    "summary": "Show Asset Discounts on Purchase Documents and Capitalize Net Values",
    "description": """
        This module preserves asset discount products as visible negative purchase document
        lines and apportions their value only when fixed assets are created from Vendor Bills.
    """,
    "author": "365 infotech",
    "website": "https://www.365infotech.co.th/",
    "category": "Purchases",
    "version": "18.0.1.2.0",
    "license": "LGPL-3",
    "depends": [
        "purchase",
        "discount_fixed_percent",
        "auto_asset_from_vendor_bill",
    ],
    "data": [
        "views/product_template_views.xml",
        "views/purchase_order_views.xml",
    ],
    "installable": True,
    "application": False,
}
