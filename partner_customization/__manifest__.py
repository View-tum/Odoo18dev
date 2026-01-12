# -*- coding: utf-8 -*-
{
    "name": "Partner Customization",
    "summary": "Partner credit/group fields for sales workflows",
    "description": """
Adds partner-level sales fields: credit rating, shop type, customer group, change-delivery-address flag, and sales memo.
    """,
    "version": "18.0.1.0.0",
    "category": "Contact",
    "author": "Phyo Thet Paing/paingphyothet561@gmail.com",
    "license": "LGPL-3",
    "website": "https://www.365infotech.co.th",
    "depends": [    
                "sale_management", 
                "account",
                "sale"
                ],
    "data": [
        "views/res_partner_views.xml",
     
    ],
    "assets": {},
    "installable": True,
    "application": False,
    "auto_install": False,
}
