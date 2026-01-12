# -*- coding: utf-8 -*-
{
    "name": "Customer Group Payment (แม่–ลูก)",
    "summary": "รับชำระเงินจากกลุ่มลูกค้าแบบบริษัทแม่–ลูก ด้วย wizard เดียว",
    "version": "18.0.1.0.0",
    "author": "Wolaprat",
    "license": "OPL-1",
    "category": "Accounting",
    "depends": ["account", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "views/account_customer_group_payment_views.xml",
    ],
    "application": False,
    "installable": True,
}
