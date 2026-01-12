# -*- coding: utf-8 -*-
{
    "name": "Purchase Request Line Discount & VATs",
    "version": "18.0.1.0.0",
    "summary": "Add Discount (%) and VATs on purchase.request.line and carry over to RFQ/PO",
    "author": "Your Team",
    "license": "OPL-1",
    "website": "https://www.365infotech.co.th",
    "depends": [
        "purchase_request",
        "account",
        "purchase",
        "purchase_request_cost",
        "purchase_request_vendor",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/purchase_request_views.xml",
    ],
    "installable": True,
    "application": False,
}
