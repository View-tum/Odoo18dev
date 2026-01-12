{
    "name": "Account: Billing Create",
    "version": "18.0.1.0.0",
    "summary": "Wizard to mass create customer billings for unpaid and partially paid invoices with date range filters.",
    "description": """
        Account Billing Custom Create
        =============================

        This module introduces a wizard to facilitate the mass creation of Billing documents (Statement of Accounts) with flexible filtering capabilities.

        **Key Features:**
        * **Date Range Filtering:** Define a specific "Start Date" and "End Date" to include invoices within a precise period.
        * **Partial Payment Support:** Automatically includes invoices with 'Partial' payment status, ensuring the remaining balances are billed.
        * **Salesperson & Customer Filters:** Generate billings specifically for customers assigned to a selected salesperson or target specific customer groups.
        * **Strict Invoice Filtering:** Focuses solely on Customer Invoices (excluding Credit Notes) to generate positive billing statements.
        * **Enhanced Logic:** Extends the standard `account.billing` model to respect the 'Start Date' criteria during line computation.
        """,
    "author": "365 infotech",
    "website": "https://www.365infotech.co.th/",
    "category": "Accounting",
    "license": "AGPL-3",
    "depends": [
        "base",
        "account",
        "account_billing",
        "partner_payment_schedule",
        "sale",
        "sale_management",
        "sales_team",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/server_action.xml",
        "views/account_billing_view.xml",
        "views/account_billing_create_view.xml",
        "views/account_menuitem.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "account_billing_create/static/src/css/notification_style.css",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
