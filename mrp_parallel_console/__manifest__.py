{
    "name": "GMP Shopfloor",
    "version": "18.0.1.0.0",
    "summary": "Parallel work order console with auto split and MRP apply.",
    "description": (
        "Provide a simplified work order console for manufacturing orders that "
        "supports parallel work centers configured on BoM operations, per work "
        "order quantities, employees, scrap, quality checks and component usage. "
        "Console quantities apply real MRP logic including stock moves and "
        "backorders using the standard Odoo button_mark_done mechanism."
    ),
    "category": "Manufacturing",
    "author": "Wolapart",
    "website": "https://365infotech.co.th",
    "license": "OPL-1",
    "depends": [
        "mrp",
        "hr",
        "stock",
        "quality",
        "web",
        "mrp_mps",
        "mrp_workorder",
        "mrp_account_enterprise",
        "maintenance",
        "mrp_maintenance",
        "bus",  # Real-time notifications
    ],
    "images": [
        "static/description/icon.png",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/mrp_parallel_console_views.xml",
        "views/mrp_work_center_management_views.xml",
        "views/stock_move_line_views.xml",
        "views/mrp_employee_cost_views.xml",
    ],
    "assets": {
        "web._assets_helpers": [
            ("after", "web/static/src/scss/utils.scss", "mrp_parallel_console/static/src/scss/bootstrap_fix.scss"),
        ],
        "web.assets_backend": [
            "mrp_parallel_console/static/src/css/mrp_parallel_console.scss",
            "mrp_parallel_console/static/src/js/mrp_parallel_console.js",
            "mrp_parallel_console/static/src/js/mps_machines_button.js",
            "mrp_parallel_console/static/src/js/mrp_more_dropdown.js",
            "mrp_parallel_console/static/src/js/stock_picking_print.js",
            "mrp_parallel_console/static/src/xml/mrp_parallel_console_templates.xml",
        ],
    },
    "installable": True,
    "application": True,
}
