{
    'name': 'PSN Purchase Request Cost',
    'version': '18.0.1.0',
    "category": "PSN-Soft/Purchase",
    'summary': 'Custom module to link Purchase Request Line with Purchase Order Line',
    'author': 'Your Name',
    'depends': ['purchase',
                'purchase_request',],  # Add necessary dependencies
    'data': [
        'views/create_rfq.xml',
    ],
    'installable': True,
    'application': False,
}
