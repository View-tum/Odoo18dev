{
    "name": "Lot Manufacturing Date",
    "version": "18.0.1.0.0",
    "summary": "Adds a manufacturing date to stock lots/serial numbers.",
    "description": """
This module extends the stock.lot model to include a 'Manufacturing Date' field,
making it visible on the form and list views.
    """,
    "category": "Inventory/Inventory ",
    "author": "Wolapart",
    "website": "https://365infotech.co.th",
    "license": "OPL-1",
    "depends": ["stock", "product_expiry"],
    "data": [
        "views/lot_manufacturing_date_views.xml",
    ],
    "installable": True,
    "application": False,
}
