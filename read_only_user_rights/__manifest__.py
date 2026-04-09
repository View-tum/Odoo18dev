# -*- coding: utf-8 -*-
# Email: sales@creyox.com
{
    'name': 'Make User Readonly For Specific Model | Limited Access Rights to Login User | Readonly Access Rights to User | Maker User Readonly',
    "author": "Creyox Technologies",
    'version': '18.0.0.0',
    'price': '35.0',
    'currency': 'USD',
    'sequence': '1',
    'category': 'Extra Tools',
    'summary': "Make User Readonly for particular model or Whole Project",
    'description':
        """
            Make User Read-only For Specific Model,
            Limited Access Rights to Login User,
            Read-only Access Rights to User,
            Maker User Read-only,
            Make User Read-only For Specific Model in Odoo,
            Limited Access Rights to Login Users in Odoo,
            Read-only Access Rights to User in Odoo,
            Maker User Read-only in Odoo,
            User Rights Configuration in Odoo,
            User Access Rights in Odoo,
            Set up User Access Rights in Odoo,
            Set up User Rights in Odoo,
            Make User Read-only in Multiple Ways,
            Read-only User,
            Read-only User in Odoo,
            Read-only Configuration in Odoo,
            Read-only Configuration,
            Specific Models Read-only,
            Specific Models Read-only in Odoo,
            Specific Model Read-only,
            Make User Read-only,
        """,
    "license": "OPL-1",
    'depends': ['base', 'sale_management'],
    'data': [
        'security/user_read_only_group.xml',
        'security/ir.model.access.csv',
        'views/res_user_read_only.xml',
    ],
    'images': [
        'static/description/banner.png'
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
