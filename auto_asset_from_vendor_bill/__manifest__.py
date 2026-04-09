{
    "name": "Auto Asset from Vendor Bill",
    "summary": "Separate action to create assets from Vendor Bills when product category is flagged.",
    "version": "18.0.2.0.0",
    "author": "Phyo Thet Paing/paingphyothet561@gmail.com",
    "website": "https://www.365infotech.co.th/",
    "license": "LGPL-3",
    "depends": [
                "account",
                "account_asset",
                "product"
        ],
    "data": [
        "security/ir.model.access.csv",
        "views/product_category_views.xml",
        "views/account_move_view.xml",
        "views/product_view.xml"
    ],
    "application": False
}
