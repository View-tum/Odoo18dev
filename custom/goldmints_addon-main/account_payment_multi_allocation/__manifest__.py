{
    "name": "Payment Register Multi-Invoice Allocation",
    "summary": "Specify payment amounts for multiple invoices in the payment register wizard",
    "version": "18.0.1.1.5",
    "author": "Wolapart",
    "license": "LGPL-3",
    "category": "Accounting",
    "depends": ["account", "bi_manual_currency_exchange_rate"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "wizard/account_payment_register_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
