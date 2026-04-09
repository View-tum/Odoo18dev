{
    'name': 'Contract Documents',
    'version': '1.0',
    'category': 'Document Management',
    'summary': 'Manage and store contract documents linked to contacts',
    'description': 'This module provides contract management for contacts, including reminders and mail logs.',
    'author': 'Your Name',
    'depends': ['base', 'mail', 'contacts', 'analytic'],
    'data': [
        'security/ir.model.access.csv',
        'data/email_template_contract_reminder.xml',
        'data/server_action_preview.xml',
        'views/contract_document_views.xml',
        'views/res_partner_views.xml',
        'views/menu_contracts.xml',
        'data/contract_reminder_cron.xml',
    ],
    # No custom JS assets; rely on standard web client behavior so popup uses the same form cleanly
    'installable': True,
    'application': False,
}
