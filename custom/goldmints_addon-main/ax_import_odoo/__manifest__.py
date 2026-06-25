{
    "name": "AX Import Odoo",
    "version": "18.0.1.0.0",
    "summary": "Import Microsoft AX voucher-form XLSX exports as Odoo journal entries",
    "description": """
AX Import Odoo
==============

Import AX voucher-form Excel exports into Odoo accounting journal entries.

Supported voucher report layouts include:
- GOE payable vouchers
- PIV payable vouchers
- GPV payment vouchers
- GRV receipt vouchers
- GPC journal/petty cash vouchers, including multi-sheet workbooks

The importer reads each sheet's voucher metadata and journal line table
(Account No., Account Description, Description, Debit, Credit), stores the
AX voucher references on the created journal entry, and can skip duplicate
vouchers that were already imported.
""",
    "category": "Accounting/Accounting",
    "author": "Phyo Thet Paing/paingphyothet561@gmail.com",
    "license": "LGPL-3",
    "depends": ["account"],
    "external_dependencies": {"python": ["openpyxl"]},
    "data": [
        "security/ir.model.access.csv",
        "views/account_move_views.xml",
        "views/ax_import_odoo_views.xml",
    ],
    "application": False,
    "installable": True,
}
