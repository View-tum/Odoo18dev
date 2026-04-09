# -*- coding: utf-8 -*-
{
    "name": "User Location Restrictions",
    "summary": "Restrict inventory users to specific warehouses, locations, and operation types",
    "description": """
Limit user access to stock operations by assigning allowed warehouses, locations,
and operation types per user. This helps prevent users from processing inventory
outside their designated areas.
""",
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
