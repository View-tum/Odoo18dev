{
    "name": "WHT Payment Auto Deduct",
    "version": "18.0.1.0.17",
    "summary": "Auto create WHT deduction from bill lines when registering payment",
    "category": "Accounting",
    "license": "AGPL-3",
    "depends": [
        "l10n_th_account_tax_multi",
        "bi_manual_currency_rate_fix",
    ],
    "data": [
        "views/account_move_views.xml",
    ],
    "installable": True,
}
