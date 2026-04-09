{
    'name': 'Product & Partner Approval with E‑Commerce Exemption',
    'summary': 'Require Accounting Manager approval for products and back‑office customers; auto‑approve e‑commerce customers.',
    'version': '18.0.1.0.0',
    'category': 'Productivity',
    "author": "Phyo Thet Paing/paingphyothet561@gmail.com",
    "website": "https://www.365infotech.co.th/",
    'license': 'LGPL-3',
    'depends': [
                'base',
                'product',
                'sale',
                'account',
                'web'
                # 'website_sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        # 'security/approval_rules.xml',
        'views/product_template_views.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'views/account_move_views.xml',
        'data/server_actions.xml'
    ],
    # "assets": {
    #     "web.assets_backend": [
    #         "your_module_name/static/src/js/lock_form_controller.js",
    #     ],
    # },
    'application': False,
    'installable': True,
}
