{
    "name": "Sale Sequence Option",
    "summary": "Manage sequence options for sale.order, i.e., quotation and order",
    "version": "18.0.1.0.0",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "development_status": "Alpha",
    "website": "https://github.com/OCA/account-financial-tools",
    "category": "Sales",
    "depends": ["sale", "base_sequence_option"],
    "data": [
        "data/sale_sequence_option.xml",
        "views/sale_order_views.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "auto_install": False,
}
