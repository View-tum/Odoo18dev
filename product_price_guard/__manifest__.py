{
    "name": "product_price_guard",
    "version": "18.0.1.0.0",
    "summary": "Add standard piece and upcharge control on products and guard purchase prices.",
    "author": "Wolapart",
    "website": "https://www.365infotech.co.th/",
    "license": "OPL-1",
    "depends": ["product", "purchase", "purchase_request"],
    "data": [
        "views/product_views.xml",
        "views/purchase_order_views.xml",
        "views/purchase_request_views.xml",
        "security/ir.model.access.csv",
    ],
    "installable": True,
}
