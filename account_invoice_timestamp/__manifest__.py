{
    "name": "Account: Invoice Timestamp",
    "version": "18.0.1.0.0",
    "summary": "Automatically records and displays timestamps for Invoices.",
    "description": 
    """ 
        Invoice Timestamp Logging
        =========================
        This module enhances invoice tracking by recording precise timestamps.

        **Key Features:**
        * **Auto-Timestamp:** Automatically logs the date and time when invoices are created or modified.
        * **Audit Trail:** Keeps a precise history of invoice timing for better traceability.
        * **Invoice Views:** Displays the timestamp directly on the invoice form.
    """,
    "author": "365 infotech",
    "website": "https://www.365infotech.co.th/",
    "category": "Accounting",
    "license": "LGPL-3",
    "depends": [
        "base",
        "account",
        "account_payment_collection_report",
        "delivery_routes_management",
        "delivery_pickup_transport",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/account_invoice_timestamp.xml",
    ],
    "assets": {},
    "installable": True,
    "application": False,
    "auto_install": False,
}