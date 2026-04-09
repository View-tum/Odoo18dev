{
    "name": "Partner Shipping&Incoterm Info",
    "summary": "Add shipping mark and incoterm to partner form",
    "description": """
Adds shipping mark and incoterm fields to the partner form to capture
shipping-related details for customers and vendors.
""",
    "author": "365 infotech",
    "website": "https://www.365infotech.co.th/",
    "category": "Contacts",
    "version": "18.0.1.0.0",
    "depends": [    
                "base",
                "contacts",
                "sale_stock"
                 ],
    "data": [
        "views/res_partner_views.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    "auto_install": False,
}
