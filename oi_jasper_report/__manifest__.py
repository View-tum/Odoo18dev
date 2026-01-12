# -*- coding: utf-8 -*-
{
'name': 'Jasper Report Integration',
'summary': 'Jasper Report Server Integration, Jasper Report, Jasper Integration, Jasper '
           'Connector, Jasper View',
'version': '18.0.1.2.2',
'category': 'Extra Tools',
'website': 'https://www.open-inside.com',
'description': '''
		execute report in jasper report server from odoo		 
    ''',
'author': 'Openinside',
'license': 'OPL-1',
'price': 69.0,
'currency': 'USD',
'installable': True,
'depends': ['web', 'oi_action_file', 'oi_pdf_viewer', 'mail'],
'data': ['views/action.xml',
          'views/res_config_settings.xml',
          'views/jasper_report.xml',
          'views/jasper_report_run.xml',
          'views/mail_template.xml',
          'views/menu.xml',
          'security/ir.model.access.csv'],
'qweb': [],
'external_dependencies': {},
'auto_install': False,
'odoo-apps': True,
'images': ['static/description/cover.png'],
'application': False
}