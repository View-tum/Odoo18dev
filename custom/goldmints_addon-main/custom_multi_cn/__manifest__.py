{
    'name': 'Multi-Invoice Credit Note',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Create a single Credit Note from multiple Vendor Bills',
    'description': """
        Allows users to select multiple Vendor Bills from the list view
        and generate a single consolidated Credit Note (in_refund).

        Features:
        - Action button appears only on Vendor Bills list view
        - Validates: same vendor, same currency, same company
        - Validates: all bills must be posted
        - Validates: no bill already reversed
        - Validates: CN date not in locked fiscal/tax period
        - Tracks reversal links back to original bills via consolidated_bill_ids
    """,
    'author': '365 Piyawat K.k',
    'depends': ['account', 'move_customer_reference'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_move_inherit_views.xml',
        'wizard/account_multi_credit_note_wizard.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
