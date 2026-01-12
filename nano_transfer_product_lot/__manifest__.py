{
    "name": "Transfer Product & Lot",
    "summary": "Transfer quantity from Product and Lot number to another Product and Lot number.",
    "version": "18.0.1.0.0",
    "category": "Nano-Dev/Nano Dev Solution",
    "website": "https://www.psn.co.th",
    "author": "Chakkrit Jansopanakul",
    "license": "LGPL-3",
    "application": False,
    'installable': True,
    "depends": ['stock'],
    "data": [
        "security/ir.model.access.csv",
        "data/repack_location.xml",
        "views/product_lot_transfer.xml"
    ],

}