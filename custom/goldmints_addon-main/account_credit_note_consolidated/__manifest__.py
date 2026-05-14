{
    "name": "Consolidated Vendor Credit Note",
    "version": "18.0.1.0.0",
    "category": "Accounting",
    "summary": "Consolidate multiple Vendor Bills and Return Pickings into a single Credit Note",
    "author": "Wolapart",
    "license": "OPL-1",
    "depends": ["account", "stock", "purchase"],
    "data": [
        "security/ir.model.access.csv",
        "wizard/account_move_consolidated_reversal_views.xml",
        "views/account_move_views.xml",
    ],
    "installable": True,
    "application": False,
}
