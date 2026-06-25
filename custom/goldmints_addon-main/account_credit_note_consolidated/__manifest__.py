{
    "name": "Consolidated Vendor Credit Note",
    "version": "18.0.2.0.0",
    "category": "Accounting",
    "summary": "Consolidate multiple Vendor Bills and Return Pickings into a single Credit Note",
    "author": "Wolapart",
    "license": "OPL-1",
    "depends": ["account", "stock", "purchase", "purchase_stock"],
    "data": [
        "security/ir.model.access.csv",
        "wizard/account_move_consolidated_reversal_views.xml",
        "wizard/account_move_reversal_views.xml",
        "views/account_move_views.xml",
        "views/stock_picking_views.xml",
    ],
    "installable": True,
    "application": False,
}
