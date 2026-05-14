# cost_sheet/__manifest__.py
{
    "name": "Cost Sheet",
    "version": "1.0",
    "author": "Piyawat K.k",
    "category": "Accounting/Inventory",
    "summary": "Module to show QWeb HTML and PDF report from a wizard",
    "depends": ["base", "web", "stock", "stock_landed_costs", "report_xlsx", "account"],
    "data": [
        "security/ir.model.access.csv",
        "views/cost_sheet_wizard_views.xml",
        "report/cost_sheet_report_views.xml",
    ],
    "assets": {
        "web.report_assets_common": [
            "cost_sheet/static/src/scss/report_cost_sheet.scss",
        ],
    },
    "installable": True,
    "application": False,
}
