# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'PSN Sales',
    'version': '18.0.0.0.1',
    'category': 'Sales/Sales',
    'depends': ['sale'],  # ✅ เพิ่มตรงนี้
    'data': [
        "security/ir.model.access.csv",
        'views/sale_order.xml',
        'views/transports.xml',
        'views/warranty.xml',
    ],
    'installable': True,
    'assets': {
        'web.assets_backend': [
            'sales_team/static/**/*',
        ],
    },
    'license': 'LGPL-3',
}
