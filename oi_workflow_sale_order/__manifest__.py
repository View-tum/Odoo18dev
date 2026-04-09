# -*- coding: utf-8 -*-
{
    'name': 'Sale Order Workflow',
    'summary': 'Sale Order Workflow, Highly Configurable and Flexible approval '
    'cycle/process for sale orders, Sale Approval, SO Approval Process, '
    'Approval Cycle, Approval Process, Sale Order, Approval Workflow, Approve '
    'Sale Order, Approve SO, Sales Manager, Multi-level Approval Process, '
    'Sale Approval Flow, Approval Rules, Manager Approval',
    'version': '18.0.16.1.10',
    'category': 'Sales/Sales/Workflow',
    'website': 'https://www.open-inside.com',
    'description': '''
Sale Order Workflow plugin
		 
    ''',
    'images': ['static/description/cover.png'],
    'author': 'Openinside',
    'license': 'OPL-1',
    'price': 49.0,
    'currency': 'USD',
    'installable': True,
    'depends': ['sale_management', 'oi_workflow'],
    'data': ['data/approval_config.xml',
             'views/sale_order.xml',
             'data/approval_buttons.xml',
             'data/mail_template.xml',
             'data/approval_automation.xml'],
    'odoo-apps': True,
    'application': False
}
