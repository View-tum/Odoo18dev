{
    "name": "Delivery Routes Management",
    "summary": "Sales regions, subregions, routes; customers use default Contacts form",
    "version": "18.0.2.0.0",
    "author": "Phyo Thet Paing/paingphyothet561@gmail.com",
    "website": "https://www.365infotech.co.th/",
    "license": "LGPL-3",
    "depends": [
                "base", 
                "hr"
                ],
    "data": [
        "security/groups.xml",
        "security/ir.model.access.csv",
        "views/sales_region_views.xml",
        "views/delivery_route_views.xml",
        "views/sub_region_views.xml",
        "views/menu.xml",
        "views/partner_views.xml"
    ],
    "application": True,
    "installable": True
}