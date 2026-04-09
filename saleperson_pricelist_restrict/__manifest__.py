{
    "name": "Saleperson Pricelist Restrict",
    "summary": "Only Sale Admin users can change pricelist on Sale Orders",
    "version": "18.0.1.0.0",
    "author": "Phyo Thet Paing/paingphyothet561@gmail.com",
    "website": "https://www.365infotech.co.th/",
    "license": "LGPL-3",
    "category": "Sales",
    "depends": ["sale_management"],
    "data": [
        "views/res_users_views.xml",
        "views/sale_order_views.xml"
    ],
    "installable": True,
    "application": False,
}
