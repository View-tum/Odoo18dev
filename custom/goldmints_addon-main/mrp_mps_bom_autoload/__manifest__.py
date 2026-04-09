{
    "name": "MRP MPS BOM Autoload",
    "version": "18.0.1.0.0",
    "summary": "Auto add all BOM components to MPS when adding a product",
    "description": """
Auto-explode multi-level BOM when adding a product to Master Production Schedule.

When a user presses Add a Product in MPS and selects a single FG,
this module will create MPS lines for:
- the selected FG
- every product in the FG's BOM tree (semifinished and components)
""",
    "author": "Wolapart",
    "license": "OPL-1",
    "depends": [
        "mrp",
        "mrp_mps",
    ],
    "data": [
        "views/res_config_settings_views.xml",
        "views/mrp_mps_bom_autoload_views.xml",
    ],
    "application": False,
    "installable": True,
}
