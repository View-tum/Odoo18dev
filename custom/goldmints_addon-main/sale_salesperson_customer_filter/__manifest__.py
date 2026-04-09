{
    "name": "Sale: Restrict Customers to Salesperson",
    "version": "18.0.1.0.0",
    "summary": "Salespeople can select only their own customers on sale orders.",
    "description": """
Restrict customer selection on sale orders so salespeople only see customers assigned to them. Sales managers keep the default unrestricted customer list.
""",
    "category": "Sales",
    "license": "LGPL-3",
    "author": "Phyo Thet Paing/paingphyothet561@gmail.com",
    "website": "https://www.365infotech.co.th/",
    "depends": [
        "sale_management",
        "account",
    ],
    "data": [
        "security/sale_salesperson_customer_filter_security.xml",
        "views/sale_order_view.xml",
        "views/account_payment_views.xml",
    ],
    "installable": True,
    "application": False,
}
