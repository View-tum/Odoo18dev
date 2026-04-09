{
    "name": "Custom UI Icon Scale",
    "version": "18.0.1.0.0",
    "category": "Hidden",
    "summary": "Adjust UI icon sizes via settings",
    "author": "Wolapart",
    "depends": ["base", "web"],
    "data": [
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "custom_ui_icon_scale/static/src/scss/icon_scale.scss",
            "custom_ui_icon_scale/static/src/js/icon_scale_loader.js",
        ],
    },
    "installable": True,
    "license": "LGPL-3",
}
