{
    "name": "Quick Create Control",
    "summary": "Control Quick Create on Many2one fields per user",
    "description": """
        Adds a checkbox in User Settings (Other tab) to globally enable/disable
        Quick Create functionality on all Many2one fields.

        When disabled, users cannot accidentally create new records by typing
        non-existent values in Many2one autocomplete fields.
    """,
    "version": "18.0.1.0.0",
    "category": "Tools",
    "author": "Wolapart",
    "website": "",
    "license": "LGPL-3",
    "depends": ["base", "web"],
    "data": [
        "views/res_users_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "quick_create_control/static/src/js/many2one_patch.js",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
