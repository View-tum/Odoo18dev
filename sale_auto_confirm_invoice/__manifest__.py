{
    "name": "Sale Auto Confirm Invoice",
    "version": "18.0.1.0.0",
    "summary": "Automatically post invoices created from sales orders",
    "description": """
Automatically confirms (posts) invoices generated from sales orders, so they don't remain in draft after delivery/invoice creation.
""",
    "category": "Sales",
    "author": "Phyo Thet Paing/paingphyothet561@gmail.com",
    "website": "https://www.365infotech.co.th/",
    "license": "LGPL-3",
    "depends": [
        "sale_management",
        "account",
    ],
    "data": [
        "views/res_config_settings_views.xml",
        "views/sale_make_invoice_advance_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "sale_auto_confirm_invoice/static/src/js/mobile_advance_payment_method.js",
        ],
    },
    "installable": True,
    "application": False,
}
