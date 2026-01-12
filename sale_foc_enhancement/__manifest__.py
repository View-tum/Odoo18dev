{
    "name": "Sale FOC Enhancement",
    "version": "18.0.1.0.0",
    "summary": "Free of Charge (FOC) sales with custom expense and COGS handling",
    "description": """
Enhances FOC handling on sales and invoices:
- Flags FOC sale/invoice lines and stores internal valuation price.
- Lets you set a dedicated COGS/expense account per company for FOC lines.
- Adjusts anglo-saxon COGS posting for FOC invoices; blocks posting if config is missing.
- Adds company and form view settings for FOC accounting.
""",
    "category": "Sales",
    "author": "Phyo Thet Paing/paingphyothet561@gmail.com",
    "website": "https://www.365infotech.co.th/",
    "license": "LGPL-3",
    "depends": [    
                "sale_management",
                 "account"
                 ],
    "data": [
        "views/res_company_view.xml",
        "views/sale_order_view.xml",
        "views/account_move_view.xml"
    ],
    "installable": True,
    "application": False
}
