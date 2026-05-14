# -*- coding: utf-8 -*-
# Copyright (C) 2020-today ITAAS (Dev K.Book)

{
    'name': 'PSN Stock Picking Line Number',
    'description': 'Add automatic numeration for Stock Picking lines',
    "version": "18.0.1.1.0",
    "category": "PSN-Soft/Stock",
    'sequence': 14,
    'summary': '',
    'author': "wattanadev",
    'website': "www.psn.co.th",
    'license': 'AGPL-3',
    'images': [
    ],
    'depends': [
        'stock',
    ],
    'data': [
        'views/stock_picking_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'psn_stock_picking_line_number/static/src/js/stock_move_lot_summary_refresh.js',
        ],
    },
    'demo': [
    ],
    'test': [
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
