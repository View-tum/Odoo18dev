{
    'name': 'Default Contact Name',
    'version': '18.0.1.0.0',
    'summary': 'Add Default Contact Name field to Partner',
    'description': 'Adds a new field "Default Contact Name" to the Contact form view.',
    'category': 'Contacts',
    'author': 'Antigravity',
    'depends': ['base', 'contacts'],
    'data': [
        'views/res_partner_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
