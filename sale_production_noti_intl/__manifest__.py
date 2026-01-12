{
    "name": "Sale Production Notification International",
    "version": "1.0",
    "category": "Manufacturing",
    "summary": "Notify production for international sales orders",
    "author": "Wolapart",
    "depends": ["sale_management", "mrp", "sale_mrp", "sale_so_type"],
    "data": [
        "views/product_template_views.xml",
        "views/mrp_production_search_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "OEEL-1",
}
