# -*- coding: utf-8 -*-
{
    "name": "Sale: Free Item Promo (Auto Bundle)",
    "summary": "Automatically add free item lines on quotations/orders if the customer is eligible.",
    "version": "18.0.1.0.0",
    "category": "Sales/Sales",
    "author": "Phyo Thet Paing",
    "website": "https://www.365infotech.co.th/",
    "license": "LGPL-3",
    "website": "https://example.com",
    "depends": [    
                "sale",
                "sale_management", 
                "product",
                "base",
                "contacts",   # partner form/base fields
                "base_vat",   # same_vat_partner_id, vat_label
                "account",    # duplicate_bank_partner_ids
                ],
    "data": [
        # "views/res_partner_views.xml",
        "views/product_template_views.xml",
        "views/sale_order_views.xml",
    ],
    "assets": {},
    "installable": True,
    "application": False,
    "auto_install": False,
}