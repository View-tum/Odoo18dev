{
    "name": "GMP Shopfloor",
    "version": "18.0.1.1.4",
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
        "mrp_workorder_hr_account",
        "maintenance",
        "mrp_maintenance",
        "mrp_mps_mo_tracking",
        "bus",
        "mrp_mold_management",
    ],

    "images": [
        "static/description/icon.png",
    ],
    "data": [
        "security/mrp_labor_cost_security.xml",
        "security/ir.model.access.csv",
        "data/ir_config_parameter.xml",
        "views/mrp_parallel_console_views.xml",
        "views/mrp_production_minimal_views.xml",
        "views/mrp_work_center_management_views.xml",
        "views/stock_move_line_views.xml",
        "views/mrp_employee_cost_views.xml",
        "views/mrp_employee_cost_analysis_views.xml",
    ],
    "assets": {
        "web._assets_helpers": [
            (
                "after",
                "web/static/src/scss/utils.scss",
                "mrp_parallel_console/static/src/scss/bootstrap_fix.scss",
            ),
        ],
        "web.assets_backend": [
            "mrp_parallel_console/static/src/css/mrp_parallel_console.scss",
            "mrp_parallel_console/static/src/js/mrp_parallel_console.js",
            "mrp_parallel_console/static/src/js/list_button_group_header.js",
            "mrp_parallel_console/static/src/js/mo_overview_employee_cost_patch.js",
            "mrp_parallel_console/static/src/js/mps_machines_button.js",
            "mrp_parallel_console/static/src/js/mrp_more_dropdown.js",
            "mrp_parallel_console/static/src/js/stock_picking_print.js",
            "mrp_parallel_console/static/src/xml/list_button_group_header.xml",
            "mrp_parallel_console/static/src/xml/mrp_parallel_console_templates.xml",
        ],
    },
    "installable": True,
    "application": True,
}
