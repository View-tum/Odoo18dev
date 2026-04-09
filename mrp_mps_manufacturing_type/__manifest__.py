{
    "name": "MPS by Manufacturing Type (Plastic / Pharma)",
    "summary": "Split Master Production Schedule by product manufacturing type (Plastic vs Pharma).",
    "version": "18.0.1.0.0",
    "category": "Manufacturing",
    "author": "Phyo Thet Paing/paingphyothet561@gmail.com",
    "website": "https://www.365infotech.co.th/",
    "license": "LGPL-3",
    "depends": [    "base",
                    "mrp_mps",
                    "product"
                    ],
    "data": [
        # "security/mps_groups.xml",
        # "security/ir.model.access.csv",
        # "security/mps_rules.xml",
        "views/product_views.xml",
        "views/mps_menus.xml",
        # "views/mps_templates.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "mrp_mps_manufacturing_type/static/src/js/mrp_mps_actions.js",
            # "mrp_mps_manufacturing_type/static/src/xml/mps_title.xml",
        ],
    },
    "installable": True,
    "application": False
}
