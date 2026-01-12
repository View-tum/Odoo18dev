# -*- coding: utf-8 -*-
{
    "name": "Interface to AX",
    "summary": "Interface to AX for GoldMints",
    "version": "18.0.1.0.0",
    "category": "Nano-Dev/Nano Dev Solution",
    "website": "https://www.psn.co.th",
    "author": "Chakkrit Jansopanakul",
    "license": "LGPL-3",
    "installable": True,
    "depends": ['base', 'sale', 'stock'],
    "data": [
        'security/ir.model.access.csv',
        'views/sale_order_view.xml',
        'views/stock_picking.xml',
        'views/report_as_finish.xml',
    ],

}
