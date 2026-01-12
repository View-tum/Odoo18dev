{
    "name": "Discount Management",
    "summary": "Discount Management for Purchase Order, Invoice and Bill.",
    "version": "18.0.1.0.0",
    "category": "Nano-Dev/Nano Dev Solution",
    "website": "https://www.psn.co.th",
    "author": "Chakkrit Jansopanakul",
    "license": "LGPL-3",
    "application": True,
    "depends": [
        'base', 'account', 'stock',
        'purchase_request',  # integrate with Purchase Request
        'purchase',
    ],
    "data": [
        'views/product_view.xml',
        'views/account.xml',
        'views/purchase.xml',
        'views/purchase_request.xml',
    ],

}
