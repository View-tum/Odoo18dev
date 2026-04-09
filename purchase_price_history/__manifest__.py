{
    "name": "Purchase Price History",
    "version": "18.0.1.0.0",
    "summary": "Smart button to view product purchase price history from PR and PO",
    "description": "Adds smart buttons on Purchase Requests and Purchase Orders to compare historical purchase prices of products.",
    "category": "Purchases",
    "author": "Wolapart",
    "website": "https://365infotech.co.th",
    "license": "OPL-1",
    "depends": [
        "purchase",
        "purchase_request",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/purchase_price_history_views.xml",
    ],
    "installable": True,
    "application": False,
}
