{
    "name": "Sale: Auto & Lock Warehouse for Van Sales",
    "summary": "Automatically assign and lock warehouse on sales orders for van sales users.",
    "version": "18.0.1.0.0",
    "category": "Sales",
    "author": "Wolapart",
    "website": "https://365infotech.co.th",
    "license": "OPL-1",
    "depends": ["sale_management", "sale_stock", "stock"],
    "data": [
        "security/groups.xml",
        "views/sale_order_view.xml",
    ],
    "application": False,
    "installable": True,
}

