{
    "name": "Currency Rate Display",
    "version": "18.0.1.0.0",
    "summary": "Displays currency rate info on SO, PO, PR, and Invoice forms",
    "description": """
        Shows selected currency's display name (e.g., USD / Buy) and
        inverse rate (e.g., 1 THB = 0.03) on Sale Order, Purchase Order,
        and Invoice forms for better visibility.
    """,
    "category": "Accounting",
    "author": "Wolapart",
    "website": "https://365infotech.co.th",
    "license": "OPL-1",
    "depends": ["bi_manual_currency_exchange_rate", "psn_currency_multirate", "purchase_request"],
    "data": [
        "views/sale_order_views.xml",
        "views/purchase_order_views.xml",
        "views/purchase_request_views.xml",
        "views/account_move_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
