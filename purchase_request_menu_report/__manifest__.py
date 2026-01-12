# purchase_request_menu_report/__manifest__.py
{
    "name": "Purchase Request Base Menu Report",
    "version": "18.0.1.0.0",
    "category": "Purchases",
    "summary": "Add Purchase Request Menu for Reports",
    "author": "Piawat K.k",
    "website": "",
    "license": "AGPL-3",
    "depends": ["purchase_request"],
    "data": [
        "views/purchase_request_menus.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
