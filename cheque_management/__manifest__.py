# -*- coding: utf-8 -*-
{
    'name': 'Cheque Management',
    'version': '18.1',
    'category': 'Cheque Management',
    'summary': 'Full cheque lifecycle for payments and receipts',
    'description': """
Manage the full lifecycle of cheques (issue, receive, deposit, return) integrated with Accounting:
- Maintain cheque books and numbering with configurable formats and sequences.
- Capture inbound/outbound cheques directly from payments and journals.
- Validate, deposit, or return cheques using guided wizards with proper access control.
- Scheduled jobs update statuses; analysis and listing reports give audit-ready visibility.
- Company-level settings for formats, defaults, and security.
""",
    'sequence': '10',
    'license': 'LGPL-3',
    "author": "Phyo Thet Paing/paingphyothet561@gmail.com",
    "website": "https://www.365infotech.co.th/",
    'depends': ['account'],
    'demo': [],
    'data': [
        'data/ir_cron.xml',
        'security/cheque_security.xml',
        'security/ir.model.access.csv',
        'data/cheque_management_seq_view.xml',
        'data/cheque_format_data.xml',
        'data/account_data.xml',
        'views/account_journal_view.xml',
        'views/menuitem_view.xml',
        'views/res_company_view.xml',
        'views/res_config_settings_view.xml',
        'views/cheque_book_view.xml',
        'reports/report_action_view.xml',
        'reports/dynamic_cheque_report_templete.xml',
        'reports/cheque_analysis_report_view.xml',
        'views/account_payment_view.xml',
        'views/dynamic_cheque_view.xml',
        'wizard/cheque_return_wizard_view.xml',
        'wizard/cheque_validate_wizard_view.xml',
        'views/cheque_inbound_outbound_view.xml',
        'views/cheque_lists_report_view.xml',
        'wizard/account_payment_register_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'images': [],
    'qweb': [],
}
