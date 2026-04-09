# -*- coding: utf-8 -*-
{
    "name": "กลุ่มบริษัท - จ่ายบิลกลุ่มบริษัท (แม่–ลูก)",
    "summary": "แม่จ่ายให้ลูก / ลูกจ่ายแทนแม่ รวมบิลหลายบริษัท จ่ายทีเดียว",
    "version": "18.0.1.0.0",
    "author": "Wolaprat",
    "license": "OPL-1",
    "category": "Accounting",
    "depends": ["account"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_company_views.xml",
        "views/account_group_payment_wizard_views.xml",
    ],
    "application": False,
    "installable": True,
}
