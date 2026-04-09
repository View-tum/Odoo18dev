{
    "name": "Account Payment Default Journal",
    "version": "18.0.1.0.0",
    "category": "Accounting",
    "summary": "Default AP/AR Journal and Payment Method settings",
    "description": """
        Configures Default Journal and Payment Method separately for Vendor Bills (AP) and Customer Invoices (AR).
    """,
    "author": "Wolapart",
    "depends": ["account"],
    "data": [
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
