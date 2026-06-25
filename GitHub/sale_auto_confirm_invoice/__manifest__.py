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
        "sale_stock",
        "account",
        "account_payment_auto_difference",
        "account_partner_settlement",
        "cheque_management",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "views/sale_make_invoice_advance_views.xml",
        "views/sale_order_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "sale_auto_confirm_invoice/static/src/js/mobile_advance_payment_method.js",
            "sale_auto_confirm_invoice/static/src/components/mobile_mixed_payment/mobile_mixed_payment.js",
            "sale_auto_confirm_invoice/static/src/components/mobile_mixed_payment/mobile_mixed_payment.xml",
            "sale_auto_confirm_invoice/static/src/components/mobile_mixed_payment/mobile_mixed_payment.scss",
        ],
    },
    "installable": True,
    "application": False,
}
