# -*- coding: utf-8 -*-

{
    'name': 'PSN Purchase Request Line Number',
    'description': 'Add automatic numeration for Purchase lines',
    'version': '18.0.1.1.0',
    "category": "PSN-Soft/Purchase Request",
    'sequence': 14,
    'summary': '',
    'license': 'AGPL-3',
    'images': [
    ],
    'depends': [
        'purchase_request',
    ],
    'data': [
        'views/purchase_request_view.xml',
    ],
    'demo': [
    ],
    'test': [
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
