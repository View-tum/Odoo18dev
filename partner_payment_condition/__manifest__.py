# -*- coding: utf-8 -*-
{
    "name": "Partner Payment Condition",
    "version": "18.0.1.0.0",
    "summary": "Extra partner payment conditions + sales notifications",
    "category": "Sales/Accounting",
    "author": "Your Team",
    "website": "https://www.365infotech.co.th",
    "license": "LGPL-3",
    "depends": ["base", "mail", "account", "sale_management", "product"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_partner_views.xml",
        # "views/product_pricelist_views.xml",
        "data/cron.xml",
    ],
    "application": False,
    "installable": True,
}
