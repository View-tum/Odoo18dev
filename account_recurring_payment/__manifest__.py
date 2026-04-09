{
    "name": "Account Recurring Payment",
    "summary": "Manage recurring payment schedules and auto-generate journal entries.",
    "version": "18.0.1.1.0",
    "category": "Accounting/Accounting",
    "author": "Goldmints",
    "license": "LGPL-3",
    "depends": ["account"],
    "data": [
        "security/ir.model.access.csv",
        "views/recurring_template_view.xml",
        "data/cron.xml"
    ],
    "installable": True,
    "application": False
}
