{
    'name': 'PSN Purchase Request Vendor',
    'version': '18.0.1.1.0',
    "category": "PSN-Soft/Purchase Request",
    'summary': 'Add vendor field to PR, copy value to PO',
    'depends': ['purchase',
                'purchase_request',],  # Add necessary dependencies
    'data': [
        'views/vendor_add.xml',
    ],
    'installable': True,
    'application': False,
}
