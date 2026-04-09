# -*- coding: utf-8 -*-
{
    "name": "Late Backorder Recovery",
    "version": "18.0.1.0.1",
    "summary": "Recover backorders after users choose no backorder by mistake.",
    "category": "Inventory/Manufacturing",
    "author": "Wolaprat",
    "license": "OPL-1",
    "depends": ["stock", "mrp"],
    "data": [
        "views/stock_picking_views.xml",
        "views/mrp_production_views.xml",
    ],
    "installable": True,
    "application": False,
}
