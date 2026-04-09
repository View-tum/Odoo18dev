{
    'name': 'Purchase Request Cost',
    'version': '18.0.1.0',
    "category": "Purchase",
    'summary': 'Custom module to link Purchase Request Line with Purchase Order Line',
    "website": "https://www.365infotech.co.th",
    'author': 'Your Name',
    "license": "LGPL-3",
    'depends': ['purchase',
                'purchase_request',],  # Add necessary dependencies
    'data': [
        'views/create_rfq.xml',
    ],
    'installable': True,
    'application': False,
}
