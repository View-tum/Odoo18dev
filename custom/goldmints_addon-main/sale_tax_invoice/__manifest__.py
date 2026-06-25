{
    "name": "Sale: Tax Invoice Button",
    "version": "18.0.1.0.0",
    "summary": "Add Tax Invoice print button to Sale Order",
    "author": "365 infotech",
    "website": "https://www.365infotech.co.th/",
    "category": "Sales",
    "license": "LGPL-3",
    "depends": ["oi_jasper_report", "sale"],
    "data": [
        "security/ir.model.access.csv",
        "views/sale_order_views.xml",
        "views/sale_tax_invoice_config_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "sale_tax_invoice/static/src/css/notification_style.css",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
