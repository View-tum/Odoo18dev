{
    'name': 'PSN Custom Kanit fonts for pdf report',
    'version': '18.0.0.1.0',
    'category': 'Fonts',
    'summary': '',
    'author': 'PSN SOFT Co., Ltd.',
    'depends':['web'],
    'assets': {
        'web.report_assets_common': [
            '/custom_fonts/static/src/scss/custom_font.scss',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}