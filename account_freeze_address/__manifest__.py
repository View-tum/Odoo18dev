# account_freeze_address/__manifest__.py
{
    "name": "Account: Freeze Address",
    "summary": "Freeze Customer/Vendor Address on Posted Invoices",
    "author": "365 infotech",
    "website": "https://www.365infotech.com",
    "category": "Accounting/Accounting",
    "version": "18.0.1.0.0",
    "depends": ["account"],
    "data": [
        "views/account_move_view.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}
