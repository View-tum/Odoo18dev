{
    "name": "MRP Product Movement Dashboard",
    "version": "18.0.1.0.0",
    "summary": "One-page product movement dashboard for production, issue, on hand and min/max.",
    "category": "Manufacturing",
    "author": "Wolapart",
    "license": "LGPL-3",
    "depends": [
        "mrp",
        "stock",
        "purchase_stock",
        "product",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "data/product_report_group_data.xml",
        "views/product_report_group_views.xml",
        "views/product_template_views.xml",
        "views/product_movement_dashboard_views.xml",
    ],
    "installable": True,
    "application": False,
}
