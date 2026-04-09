# -*- coding: utf-8 -*-
{
    "name": "User Location Restrictions",
    "summary": "Restrict inventory users to specific warehouses, locations, and operation types",
    "version": "18.0.1.0.0",
    "category": "Inventory/Inventory",
    "author": "Phyo Thet Paing/paingphyothet561@gmail.com",
    "license": "LGPL-3",
   'website': 'https://www.365infotech.co.th/',
    "depends": ["stock"],
    "data": [
        "security/user_location_restrictions_security.xml",
        "security/ir.model.access.csv",
        "views/res_users_views.xml",
    ],
    "installable": True,
    "application": False,
}