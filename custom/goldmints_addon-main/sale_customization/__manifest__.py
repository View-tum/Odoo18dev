{
    "name": "Sale customization",
    "summary": "Add Document Number field to Sales Orders",
    "description": """
Add logistics helper fields to the sales order form to capture shipping gross weight and number of cartons. The fields are shown after the commitment date on the order form so users can record packing details alongside the order.
""",
    "version": "18.0.1.0.0",
    "category": "Sales",
    "author": "Phyo Thet Paing/paingphyothet561@gmail.com",
    "website": "https://www.365infotech.co.th/",
    "license": "LGPL-3",
    "installable": True,
    "depends": [
                "base", 
                "contacts", 
                "sale",
                "delivery",
                "partner_shipping_info"
                 ],
    "data": [
        "views/sale_order_view.xml",
    ],
}
