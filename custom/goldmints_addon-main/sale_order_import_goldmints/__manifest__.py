{
    "name": "Goldmints Sale Order Import",
    "version": "18.0.1.0.0",
    "summary": "Import sale orders and lines from XLSX with Goldmints fields",
    "description": """
Import sale orders from XLSX
---------------------------------
- Upload XLSX with columns: id, document_ref, partner_id (and invoice/shipping), dates, payment terms, sale_note, SO type, warehouse, salesperson.
- Supports order lines with product, quantity, price, and discount.
- Can update existing draft orders (by name or document_ref) when enabled.
""",
    "category": "Sales",
    "author": "Phyo Thet Paing/paingphyothet561@gmail.com",
    "license": "LGPL-3",
    "website": "https://www.365infotech.co.th/",
    "depends": [
        "sale_management",
        "sale_document_ref",
        "sale_note_carry_info",
        "sale_so_type",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/sale_order_import_wizard_views.xml",
    ],
    "assets": {},
    "external_dependencies": {"python": ["openpyxl", "pandas"]},
    "installable": True,
    "application": False,
}
