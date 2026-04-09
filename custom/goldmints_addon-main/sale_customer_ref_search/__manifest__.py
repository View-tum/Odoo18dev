{
    "name": "Sale Customer Reference Search",
    "version": "18.0.1.0.0",
    "summary": "Show customer reference before the name when choosing customers on sale orders",
    "description": """
Displays the customer reference (ref) before the name in sale order customer selection.

- Adds a context flag on the sale order customer field to include the partner reference.
- Overrides partner display to show "REF -> Name" when picking customers with identical names.
    """,
    "category": "Sales",
    "author": "Phyo Thet Paing/paingphyothet561@gmail.com",
    "website": "https://www.365infotech.co.th/",
    "license": "LGPL-3",
    "depends": [
        "sale_management",
    ],
    "data": [
        "views/sale_order_view.xml",
    ],
    "installable": True,
    "application": False,
}
