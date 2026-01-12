{
    "name": "Precision Control",
    "version": "18.0.3.0.0",
    "summary": "Configurable decimal precision for Sale, Purchase, and MRP modules.",
    "category": "Customization",
    "author": "Wolapart",
    'depends': ['base_setup', 'sale', 'purchase', 'mrp', 'web', 'account', 'purchase_request', 'purchase_request_line_discount_taxes'],
    'data': [
        'views/res_config_settings_views.xml',
        'views/purchase_request_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'precision_control/static/src/js/precision_policy.js',
        ],
    },
    "installable": True,
    "license": "LGPL-3",
}
