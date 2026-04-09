# -*- coding: utf-8 -*-

{
    "name": "Account Discount Single Line",
    "summary": "Show gross revenue line and hide discount allocation revenue lines",
    "description": """
Shows a single gross revenue line in invoice journal items by hiding the
discount allocation revenue lines and displaying gross debit/credit values.
    """,
    "version": "18.0.1.0.0",
    "category": "Accounting",
    "author": "Phyo Thet Paing/paingphyothet561@gmail.com",
    "license": "LGPL-3",
    "website": "https://www.365infotech.co.th",
    "depends": [
        "account",
    ],
    "data": [
        "views/account_move_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
