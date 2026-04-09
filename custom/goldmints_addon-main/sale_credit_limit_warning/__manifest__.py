{
    "name": "Partner Credit Limit - Warning",
    "summary": "Customer and company-group credit warning on quotations.",
    "description": """
Credit limit warning for Sales Orders / Quotations.

Features
- Computes Customer and Company Group credit metrics:
  - Credit Limit
  - Credit Used (Invoiced)
  - Credit Used (SO Approved)
  - Credit Balance
- Displays warning when:
  - Credit Balance - Current SO < 0
- Adds "Check Credit" button on quotation to force credit details banner.
- Works with company-group structure using group members for consolidated exposure.
""",
    "version": "18.0.1.0.0",
    "author": "Phyo Thet Paing/paingphyothet561@gmail.com",
    "website": "https://www.365infotech.co.th/",
    "license": "LGPL-3",
    "category": "Sales/Sales",
    "depends": [
        "sale",
        "company_group_structure",
    ],
    "data": [
        "views/sale_order_views.xml",
    ],
    "application": False,
    "installable": True
}
