{
    'name': 'Sale Default Analytic Distribution',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Set default analytic distribution in Sale Settings',
    'description': """
        Allows configuring a default analytic account in Sale Settings.
        This account is automatically applied to Sale Order Lines when a product is selected.
    """,
    'author': 'Trae AI',
    'depends': ['sale', 'account'],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
