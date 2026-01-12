
# -*- coding: utf-8 -*-
{
    'name': 'Delivery & Pickup Transport Forms',
    'summary': 'Simple A4 PDF forms for inter-warehouse delivery and carrier pickup (no states/attrs).',
    'version': '1.0.0',
    'category': 'Inventory/Operations',
    "author": "Phyo Thet Paing/paingphyothet561@gmail.com",
    "website": "https://www.365infotech.co.th/",
    'license': 'LGPL-3',
    'depends': [
                'base', 
                'stock',
                'delivery_routes_management',
                'hr'
                ],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'reports/delivery_reports.xml',
        'views/delivery_send_view.xml',
        'views/transport_pickup_view.xml',
        'views/customer_parcel_list_view.xml',
        'views/menu.xml'
    ],
    'installable': True,
    'application': False,
}
