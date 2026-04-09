{
    "name": "Purchase Receipt Migration Import",
    "summary": "Import purchase orders and incoming receipts with lot and location validation",
    "version": "18.0.1.0.0",
    "category": "Purchases",
    "author": "OpenAI",
    "license": "LGPL-3",
    "depends": ["purchase_stock"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "views/purchase_receipt_migration_views.xml",
    ],
    "installable": True,
    "application": False,
}
