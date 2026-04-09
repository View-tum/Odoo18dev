{
    "name": "MRP Scrap Landed Cost Allocation",
    "version": "18.0.1.0.0",
    "category": "Manufacturing",
    "summary": "Allocate scrap cost back to FG via Landed Costs",
    "author": "Wolapart",
    "depends": ["mrp", "stock_landed_costs", "mrp_landed_costs"],
    "data": [
        "security/ir.model.access.csv",
        "views/product_views.xml",
        "views/mrp_production_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}
