# -*- coding: utf-8 -*-
{
    'name': 'Sale Order Payments Smart Button',
    'version': '1.0',
    'summary': 'Add a Payments smart button on Sale Order form',
    'description': 'Compute related payments from invoices and show a smart button on sale.order',
    'category': 'Sales',
    'author': 'Your Name',
    'license': 'LGPL-3',
    'depends': ['sale', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
