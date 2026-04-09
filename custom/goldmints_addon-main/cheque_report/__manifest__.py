# -*- coding: utf-8 -*-
{
    "name": "Cheque Report",
    "summary": "Report Jasper for Cheque Management",
    "version": "18.0.1.0.0",
    "author": "365 infotech",
    "website": "https://www.365infotech.co.th/",
    "category": "Accounting",
    "depends": [
        "base",
        "account",
        "cheque_management",
        "oi_jasper_report",
    ],
    "data": [
        "security/ir.model.access.csv",
        "report/cheque_report_view.xml",
        "views/cheque_inbound_outbound_view.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}
