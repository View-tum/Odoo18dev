{
    "name": "MPS by Manufacturing Type (Plastic / Pharma)",
    "summary": "Split Master Production Schedule by product manufacturing type (Plastic vs Pharma).",
    "description": "Split Master Production Schedule by product manufacturing type (Plastic vs Pharma).",
    "version": "18.0.1.1.0",
    "category": "Manufacturing",
    "author": "Phyo Thet Paing/paingphyothet561@gmail.com",
    "website": "https://www.365infotech.co.th/",
    "license": "LGPL-3",
    "depends": [
        "base",
        "mrp_mps",
        "product",
        "mrp_auto_merge",
        "mrp_parallel_console",
        "sale_so_type",
        "purchase",
    ],
    "data": [
        "security/mps_groups.xml",
        "data/sm_pharma_sync.xml",
        "views/res_users_views.xml",
        "views/product_views.xml",
        "views/mps_menus.xml",
        "views/mrp_production_views.xml",
        "views/mrp_workcenter_views.xml",
        "views/shop_floor_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "mrp_mps_manufacturing_type/static/src/js/mrp_mps_actions.js",
            "mrp_mps_manufacturing_type/static/src/js/mrp_parallel_console_patch.js",
        ],
    },
    "installable": True,
    "application": False
}
