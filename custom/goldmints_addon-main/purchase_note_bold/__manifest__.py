{
    'name': 'Bold Purchase Notes Placeholder',
    'version': '18.0.1.0.0',
    'category': 'Purchase',
    'summary': 'Make placeholder text in Purchase Note bold and larger',
    'author': '365 Piyawat K.k',
    'depends': ['purchase', 'web'],
    'data': [
        'views/purchase_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'purchase_note_bold/static/src/css/style.css',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}