{
    'name': 'PO Service Indicator',
    'version': '18.0.1.0.0',
    'summary': 'Show separate statusbar when PO contains service lines',
    'author': '365 Infotech',
    'website': 'https://www.365infotech.co.th',
    'category': '365infotech/Purchase Management',
    'license': 'LGPL-3',
    'depends': ['purchase'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/validate_service.xml',
        'views/purchase.xml',
    ],
    'installable': True,
    'application': False,
}
