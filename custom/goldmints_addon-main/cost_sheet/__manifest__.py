# cost_sheet/__manifest__.py
{
    "name": "Cost Sheet",
    "version": "1.0",
    "author": "Your Name",
    "website": "https://example.com",
    "category": "Accounting/Inventory",
    "summary": "Demo module to show QWeb HTML and PDF report from a wizard",
    "depends": ["base", "web", "stock"],
    "data": [
        "security/ir.model.access.csv",
        "views/cost_sheet_wizard_views.xml",
        "report/cost_sheet_report_views.xml",
    ],
    "installable": True,
    "application": False,
}
