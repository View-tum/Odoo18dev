{
    "name": "Precision Control",
    "version": "18.0.3.1.15",
    "summary": "Configurable decimal precision for Sale, Purchase, and MRP modules.",
    "category": "Customization",
    "author": "Wolapart",
    'depends': ['base_setup', 'sale', 'purchase', 'mrp', 'web', 'account', 'account_reports', 'purchase_request', 'purchase_request_line_discount_taxes', 'spreadsheet'],
    'data': [
        'views/res_config_settings_views.xml',
        'views/purchase_request_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'precision_control/static/src/js/precision_settings.js',
            'precision_control/static/src/js/precision_policy.js',
        ],
        'spreadsheet.o_spreadsheet': [
            'precision_control/static/src/js/precision_settings.js',
            'precision_control/static/src/js/precision_spreadsheet.js',
        ],
    },
    "installable": True,
    "license": "LGPL-3",
}
