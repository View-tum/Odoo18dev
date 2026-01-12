# -*- coding: utf-8 -*-
{
    "name": "Inventory Stock Count Report",
    "summary": "Printable stock count sheet (PDF) and Excel export by location, for manual counting",
    "version": "18.0.1.0",
    "category": "Inventory/Reporting",
    "author": "Piyawat K.k",
    "license": "LGPL-3",
    "depends": ["stock", "web", "base"],
    "data": [
        "security/ir.model.access.csv",
        "views/stock_count_report_wizard_views.xml",
        "reports/actions/stock_count_paperformat.xml",
        "reports/actions/stock_count_report_actions.xml",
        "reports/templates/stock_count_report_templates.xml",
    ],
    "assets": {
        "web.report_assets_common": [
            "inventory_stock_count_report/static/src/scss/report_template.scss",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
