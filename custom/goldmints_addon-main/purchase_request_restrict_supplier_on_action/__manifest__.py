# -*- coding: utf-8 -*-
{
    "name": "PR: Restrict Supplier on Create RFQ",
    "summary": "Block Create RFQ from Purchase Request Lines with mixed suppliers (hook at wizard).",
    "version": "1.0.1",
    "category": "Purchases",
    "author": "YourName",
    "website": "https://www.365infotech.co.th",
    "license": "LGPL-3",
    "depends": [
        "purchase_request",  # OCA module for Purchase Request
        "purchase",
    ],
    "data": [],
    "installable": True,
    "application": False,
}
