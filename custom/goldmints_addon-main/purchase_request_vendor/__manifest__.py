{
    'name': 'Purchase Request Vendor',
    'version': '18.0.1.1.0',
    "category": "Purchase Request",
    'summary': 'Add vendor field to PR, copy value to PO',
    "author": "365 Infotech",
    "website": "https://www.365infotech.co.th",
    "license": "LGPL-3",
    'depends': ['purchase',
                'purchase_request',],  # Add necessary dependencies
    'data': [
        'views/vendor_add.xml',
    ],
    'installable': True,
    'application': False,
}
