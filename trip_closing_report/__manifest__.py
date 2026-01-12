# -*- coding: utf-8 -*-
{
    "name": "Inventory: Trip Closing Report",
    "summary": "Trip Closing report for sales truck trips",
    "description": """
    Trip Closing Report
    ==========================

    - Wizard to select date range and sales truck
    - QWeb PDF report with:
    - Page 1: A4 landscape product summary
    - Page 2+: A4 portrait money summary and bank transfer details
    """,
    "author": "Piyawat K.k",
    "website": "",
    "category": "Reporting",
    "version": "1.0",
    "license": "LGPL-3",
    "depends": [
        "base",
        "web",
        "sale_management",
        "account",  
        "stock",
        "hr",
    ],
    "assets": {
        "web.report_assets_common": [
            "trip_closing_report/static/src/css/trip_closing_report.css",
        ],
    },
    "data": [
        "security/ir.model.access.csv",
        "views/trip_closing_wizard_views.xml",
        "report/trip_closing_report.xml",
        "report/trip_closing_templates.xml",
    ],
    "installable": True,
    "application": False,
}
