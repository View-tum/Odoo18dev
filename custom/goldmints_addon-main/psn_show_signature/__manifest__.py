{
    'name': 'PSN Show Signature',
    'version': '18.0.1.0.0',
    'summary': """ PSN Show Signature """,
    'author': 'PSN SOFT Co., Ltd.',
    'website': 'https://psnsoft.com/',
    'depends': ['purchase', 'base', 'web'],
    'data': [
        'views/signature_view.xml',
        'security/ir.model.access.csv',
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}

