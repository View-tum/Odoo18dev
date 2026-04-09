{
    "name": "Project Budget Blocking",
    "summary": "Block Expense if Project Budget (Standard) is exceeded",
    "version": "18.0.1.0.0",
    "category": "Accounting/Budget",
    "author": "365 infotech",
    "website": "https://www.365infotech.co.th/",
    "license": "LGPL-3",
    "depends": [
        "account_budget",
        "hr_expense",
        "project",
        "project_account_budget",
        "purchase_request",
    ],
    "data": [],
    "assets": {
        "web.assets_backend": [
            "project_budget_block/static/src/css/notification_style.css",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
