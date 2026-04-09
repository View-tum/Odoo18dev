# -*- coding: utf-8 -*-
{
    'name': "Salesperson Signature & Stamp",

    'summary': """Show sign and stamp on the reports.""",

    'description': """This module gives you option to show salesperson signature and company stamp on the sale order,
     invoice and delivery orders. By using the signature widget users and add their signature.""",

    'author': "ErpMstar Solutions",
    "category": "PSN-Soft/Sale",
    'version': '18.0.1.0',

    # any module necessary for this one to work correctly
    'depends': ['sale_management', 'stock', "purchase"],

    # always loaded
    'data': [
        'views/users_view.xml',
        'views/company_stamp.xml',
        'reports/sale_report_template_sign_stamp.xml',
        'reports/account_report_template_sign_stamp.xml',
        'reports/stock_report_template_sign_stamp.xml',
        'reports/purchase_report_template_sign_stamp.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
    'images': ['static/description/banner.jpg'],
    'installable': True,
    'application': True,
    'price': 16,
    'currency': 'EUR',
}
