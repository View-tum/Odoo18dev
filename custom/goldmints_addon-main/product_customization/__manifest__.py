{
    "name": "Product customization",
    "summary": "Add Additional field to Product",
    "description": """
Add logistics helper fields on the product template to capture gross weight and package dimensions alongside the existing weight/volume info.
""",
    "version": "18.0.1.0.0",
    "category": "Inventory",
    "author": "Phyo Thet Paing/paingphyothet561@gmail.com",
    "website": "https://www.365infotech.co.th/",
    "license": "LGPL-3",
    "installable": True,
    "depends": [
        "product",
        "stock",
    ],
    "data": [
        "views/product_template_views.xml",
    ],
}
