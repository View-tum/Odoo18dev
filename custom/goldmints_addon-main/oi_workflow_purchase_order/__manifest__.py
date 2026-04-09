# -*- coding: utf-8 -*-
{
'name': 'Purchase Order Workflow',
'summary': 'Purchase Order Workflow, Highly Configurable and Flexible approval '
           'cycle/process for purchase orders, Purchase Approval, PO Approval Process, '
           'Approval Cycle, Approval Process, Purchase Order, Approval Workflow, Approve '
           'Purchase Order, Approve PO, Purchase Manager, Multi-level Approval Process, '
           'Purchase Approval Flow, Approval Rules, Manager Approval',
'version': '18.0.16.1.10',
'category': 'Inventory/Purchase/Workflow',
'website': 'https://www.open-inside.com',
'description': '''
Purchase Order Workflow plugin
		 
    ''',
'images': ['static/description/cover.png'],
'author': 'Openinside',
'license': 'OPL-1',
'price': 49.0,
'currency': 'USD',
'installable': True,
'depends': ['purchase', 'oi_workflow'],
'data': ['data/approval_config.xml',
          'views/purchase_order.xml',
          'data/approval_buttons.xml',
          'data/mail_template.xml',
          'data/approval_automation.xml'],
'odoo-apps': True,
'application': False
}