{
    "name": "MO Production Summary",
    "version": "18.0.1.0.0",
    "category": "Manufacturing",
    "summary": "Comprehensive MO Production Summary with full traceability",
    "description": "List view showing materials, labor, costs, and vendor/MO traceability for Manufacturing Orders.",
    "author": "Wolapart",
    "license": "LGPL-3",
    "depends": ["mrp", "stock", "purchase", "sale", "mrp_account_enterprise"],
    "data": [
        "security/ir.model.access.csv",
        "views/mrp_production_summary_views.xml",
        "views/mrp_production_views.xml",
        "views/mrp_report_views.xml",
    ],
    "installable": True,
    "auto_install": False,
}
