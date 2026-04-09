{
    "name": "Manufacturing: Lead Time",
    "summary": "Manage Manufacturing Lead Time on Products and Propagate to Sales Lines",
    "description": """
Manufacturing Lead Time Management
==================================
This module allows you to define a specific 'Manufacturing Lead Time' (in days) 
directly on the Product Template.

Key Features:
-------------
* **Product Configuration**: Define MFG Lead Time for each product in the Inventory tab.
* **Auto-Propagation**: Automatically fetches the lead time value to the Sales Order Line when a product is selected.
    """,
    "version": "18.0.1.0.0",
    "category": "Manufacturing/Manufacturing",
    "author": "365 infotech",
    "website": "https://www.365infotech.co.th/",
    "license": "LGPL-3",
    "depends": [
        "base",
        "sale",
        "product",
    ],
    "data": ["views/product_template_views.xml", "views/sale_order_line_views.xml"],
    "assets": {},
    "installable": True,
    "application": False,
    "auto_install": False,
}
