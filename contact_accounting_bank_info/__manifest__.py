{
    "name": "Contact Accounting Bank Info",
    "version": "1.0.0",
    "author": "Piyawat K.k",
    "category": "Contacts",
    "summary": "Add Banker / Remittance Information field to contacts (res.partner)",
    "description": "Adds a multiline text field for bank/remittance info to res.partner, shown in Accounting tab or Banking Information tab.",
    "depends": [
        "contacts",
        "account",
    ],
    "data": [
        "views/res_partner_view.xml"
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3"
}
