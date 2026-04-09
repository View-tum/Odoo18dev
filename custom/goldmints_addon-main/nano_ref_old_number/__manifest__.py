{
    "name": "Reference old system number ",
    "summary": "Reference document number from old system.",
    "version": "18.0.1.0.0",
    "category": "Nano-Dev/Nano Dev Solution",
    "website": "https://www.psn.co.th",
    "author": "Chakkrit Jansopanakul",
    "license": "LGPL-3",
    "application": True,
    "depends": [
        'base', 'account', 'purchase', 'sale', 'stock', 'l10n_th_account_tax'
    ],
    "data": [
        'views/account_move.xml',
        'views/account_payment.xml',
        'views/purchase_order.xml',
        'views/sale_order.xml',
    ],

}
