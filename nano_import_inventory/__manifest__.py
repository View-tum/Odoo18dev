{
    "name": "Import Inventory",
    "summary": "Import Inventory transaction.",
    "version": "18.0.1.0.0",
    "category": "Nano-Dev/Nano Dev Solution",
    "website": "https://www.psn.co.th",
    "author": "Chakkrit Jansopanakul",
    "license": "LGPL-3",
    "application": True,
    "depends": [
        'base', 'account', 'purchase', 'stock', 'l10n_th_account_tax'
    ],
    "data": [
        'security/ir.model.access.csv',
        'views/res_config_settings.xml',
        'views/thecool_rereceive_import.xml',
    ],

}
