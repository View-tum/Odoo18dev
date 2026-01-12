# -*- coding: utf-8 -*-
{
    "name": "Stock Internal Validate Guard",
    "version": "18.0.1.0.0",
    "summary": "Restrict 'Validate' button on Internal Transfers by Operation Type and Groups.",
    "description": "Adds per-Operation Type controls to restrict who can validate Internal Transfers. "
                   "Includes a Settings UI to configure allowed groups per internal Operation Type. ",
    "category": "Customization",
    "author": "Wolapart",
    "website": "https://365infotech.co.th",
    "license": "OPL-1",
    "depends": ["base", "stock"],
    "data": [
        "security/ir.model.access.csv",
        "views/stock_internal_validate_guard_views.xml",
    ],
    "installable": True,
    "application": False,
}
