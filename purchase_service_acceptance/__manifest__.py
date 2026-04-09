{
    'name': 'Purchase Service Acceptance',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Purchase',
    'summary': 'Manage Service Acceptance for Purchase Orders',
    'description': """
        This module allows you to create Service Acceptance records for Purchase Orders.
        It serves as a "Receipt" for service products, updating the received quantity on the PO line.
    """,
    'author': 'Antigravity',
    'depends': ['purchase', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/service_acceptance_view.xml',
        'views/purchase_order_view.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
