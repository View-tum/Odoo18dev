# -*- coding: utf-8 -*-
{
    "name": "Contact: Show Parent Company Field",
    "summary": "Show the 'Parent Company' (parent_id) on res.partner form/tree for Odoo 18",
    "version": "18.0.1.0.0",
    "author": "Wolapart",
    "website": "https://www.365infotech.co.th/",
    "license": "OPL-1",
    "category": "Contacts",
    "depends": ["base"],
    "data": [
        "views/res_partner_views.xml",
        "security/ir.model.access.csv",
    ],
    "application": False,
    "installable": True,
}

