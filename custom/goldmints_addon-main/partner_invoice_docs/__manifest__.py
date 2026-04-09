# partner_invoice_docs/__manifest__.py
{
    "name": "Partner Invoice Documents",
    "summary": "Add invoice supporting documents tab to partner form",
    "author": "365 infotech",
    "website": "https://www.365infotech.co.th/",
    "category": "partner",
    "version": "18.0.1.0.0",
    "depends": ["base", "contacts"],
    "data": [
        "views/res_partner_views.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    "auto_install": False,
}
