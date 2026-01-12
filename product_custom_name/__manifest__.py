{
    "name": "Product Referrence Custom Name",
    "version": "1.0",
    "depends": ["product", "web"],
    "data": [
        "views/product_template_view.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "product_custom_name/static/src/js/auto_focus.js",
        ],
    },
    "installable": True,
    "application": False,
}
