{
    "name": "Sale Order Simulation (Shadow Mode)",
    "summary": "Create temporary shadow records of Sale Orders for ad-hoc editing and printing.",
    "version": "18.0.1.0.0",
    "category": "Sales",
    "author": "Wolapart",
    "website": "https://www.wolapart.com",
    "license": "LGPL-3",
    "depends": ["sale", "sale_extra_info"],
    "data": [
        "data/ir_cron.xml",
        "views/sale_order_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
