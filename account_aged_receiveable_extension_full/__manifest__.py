# -*- coding: utf-8 -*-
{
    "name": "Account: Aged Receiveable Extension Full",
    "summary": "Add Payment Condition (Extra Days) and Partner Payment Schedule logic to Aged Report",
    "author": "365 infotech",
    "website": "https://www.365infotech.co.th/",
    "category": "Accounting/Accounting",
    "version": "18.0.1.0.0",
    "depends": [
        "account_aged_receiveable_extension",
        "partner_payment_schedule",
        "partner_payment_condition",
    ],
    "data": [
        "wizard/account_aged_receiveable_extension_view.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    "auto_install": False,
}
