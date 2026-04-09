# -*- coding: utf-8 -*-
{
    "name": "Account Test Runner",
    "summary": "Run and store accounting/custom integration test results in Odoo",
    "version": "18.0.1.0.0",
    "category": "Accounting/Accounting",
    "author": "Goldmints",
    "license": "LGPL-3",
    "depends": ["account", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "views/qa_account_test_run_views.xml",
    ],
    "application": False,
    "installable": True,
}
