# -*- coding: utf-8 -*-
{
    "name": "Sale Invoice Pending Payment",
    "summary": """
        Check and list invoices with 'In Payment' status by customer.
    """,
    "description": """
        This module provides a wizard to search for invoices currently in the 'In Payment' status.
        Users can filter results by customer to easily track pending payments or checks.
        
        Key Features:
        - Filter invoices by Customer.
        - Display key invoice details: Number, Date, Amount, and Status.
        - Direct link to the 'In Payment' invoices.
    """,
    "author": "365 infotech",
    "website": "https://www.365infotech.co.th/",
    "category": "Sales/Sales",
    "version": "18.0.1.0.0",
    "depends": ["base", "sale", "account", "account_invoice_timestamp"],
    "data": [
        "security/ir.model.access.csv",
        "wizard/sale_invoice_pending_payment_view.xml",
        "views/sale_menus.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    "auto_install": False,
}
