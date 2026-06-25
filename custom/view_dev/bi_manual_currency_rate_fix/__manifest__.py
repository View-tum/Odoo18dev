{
    "name": "BI Manual Currency Exchange Rate Fix",
    "version": "18.0.1.0.7",
    "category": "Accounting",
    "summary": "Comprehensive fix for Entry Balance Error, THB display, WHT Manual Rate",
    "author": "Wolapart",
    "license": "LGPL-3",
    "depends": [
        "bi_manual_currency_exchange_rate",
        "l10n_th_account_tax",
        "account_payment_multi_deduction",
        "l10n_th_account_tax_multi",
        "account_debit_note",
    ],

    "data": [
        "views/res_config_settings_views.xml",
        "views/account_payment_register_views.xml",
        "views/account_move_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False
}
