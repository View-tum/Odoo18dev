{
    "name": "Sale Note Carry Info",
    "summary": "Add a note field on Sale Order and carry it to Pickings, Moves, and Invoices",
    "description": "Adds an internal sales note and propagates it to deliveries, stock moves, and invoices.",
    "version": "18.0.1.0.0",
    "author": "Phyo Thet Paing/paingphyothet561@gmail.com",
    "license": "LGPL-3",
    "website": "https://www.365infotech.co.th/",
    "category": "Sales",
    "depends": [    
                "sale_management", 
                "stock", 
                "account",
                "sale",
                "mrp"
                ],
    "data": [
        "views/sale_order_view.xml",
        "views/stock_picking_view.xml",
        "views/stock_move_view.xml",
        "views/account_move_view.xml",
        "views/mrp_production_view.xml",
    ],
    "installable": True,
    "application": False,
}
