{
    "name": "Purchase Note Carry Info",
    "summary": "Add a purchase note on Purchase Orders and carry it to Receipts, Moves, and Vendor Bills",
    "version": "18.0.1.0.0",
    "author": "Wolapart",
    "license": "LGPL-3",
    "website": "https://www.365infotech.co.th/",
    "category": "Purchases",
    "depends": [
        "purchase_stock",
        "account",
        "purchase_request",
    ],
    "data": [
        "views/purchase_request_view.xml",
        "views/purchase_order_view.xml",
        "views/stock_picking_view.xml",
        "views/stock_move_view.xml",
        "views/account_move_view.xml"
    ],
    "installable": True,
    "application": False
}
