{
    "name": "Company Group Structure",
    "version": "18.0.1.0.0",
    "summary": "Company structure view for contacts",
    "description": "Adds a separate company structure view using res.partner parent/child.",
    "category": "Contacts",
    "author": "Phyo Thet Paing/paingphyothet561@gmail.com",
    "website": "https://www.365infotech.co.th/",
    "license": "LGPL-3",
    "depends": ["base", "contacts", "account", "sale"],
    "data": [
        "views/res_partner_views.xml",
    ],
    "installable": True,
    "application": False,
}
