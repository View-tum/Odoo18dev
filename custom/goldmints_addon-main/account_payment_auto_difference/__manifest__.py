# -*- coding: utf-8 -*-
{
    'name': 'Account Payment Auto Difference',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Automatically pre-fill multi deductions when there is a payment difference.',
    'description': """
        This module allows users to configure a default account and label for payment differences
        in the Accounting Settings. When registering a payment, if a difference is detected,
        it will automatically append a line to the Multi-Deduction tab using the configured account.
    """,
    'author': 'Wolapart',
    'depends': [
        'account',
        'account_payment_multi_deduction',
    ],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
