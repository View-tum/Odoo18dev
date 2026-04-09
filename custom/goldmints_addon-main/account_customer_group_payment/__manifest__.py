# -*- coding: utf-8 -*-
{
    "name": "Customer Group Payment",
    "summary": "รับชำระเงินจากกลุ่มลูกค้าแบบบริษัท ด้วย wizard เดียว",
    "version": "18.0.1.0.0",
    "author": "Wolaprat",
    "license": "OPL-1",
    "category": "Accounting",
    "depends": ["account", "mail", "company_group_structure", "cheque_management", "sale_customer_ref_search"],
    "data": [
        "security/ir.model.access.csv",
        "views/account_customer_group_payment_views.xml",
    ],
    "application": False,
    "installable": True,
}
