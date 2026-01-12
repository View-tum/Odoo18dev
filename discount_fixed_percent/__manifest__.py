# -*- coding: utf-8 -*-
{
    "name": "Fixed & Percentage Discount on Lines",
    "summary": "Manage Fixed Amount & Percentage Discounts on PR, PO, SO, and Invoices",
    "description": """
        Fixed & Percentage Discount Module
        ==================================
        Extends Odoo standard discount functionality to support:
        1. Fixed Amount Discount (THB/Currency): Auto-calculates percentage.
        2. Percentage Discount (%): Auto-clears fixed amount.
        3. Workflow Propagation: values pass from PR -> PO -> Bill and SO -> Invoice.
        4. Partial Invoicing: Fixed discount amount is pro-rated based on invoiced quantity.
    """,
    "author": "365 infotech",
    "website": "https://www.365infotech.co.th/",
    "category": "Sales/Sales",
    "version": "18.0.1.0.2",
    "license": "LGPL-3",
    "application": False,
    "installable": True,
    "auto_install": False,
    "depends": [
        "base",
        "account",
        "purchase",
        "purchase_request_line_discount_taxes",
        "sale",
    ],
    "data": [
        "views/account_move_view.xml",
        "views/purchase_order_view.xml",
        "views/purchase_request_view.xml",
        # "views/sale_order_view.xml",
    ],
}
