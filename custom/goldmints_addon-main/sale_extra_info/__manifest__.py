{
    "name": "Sale Order Extra Info",
    "version": "18.0.1.0.0",
    "summary": "Adds Proforma, Reference PI, and Credit Balance to SO Other Info",
    "description": """
        Adds the following fields to the Sale Order 'Other Info' tab:
        - Proforma Invoice No.
        - Reference PI
        - Partner Credit Balance (Readonly from Accounting)
    """,
    "category": "Sales",
    "author": "Wolapart",
    "website": "https://365infotech.co.th",
    "license": "OPL-1",
    "depends": ["sale_management", "account", "sale_so_type"],
    "data": [
        "data/ir_sequence_data.xml",
        "views/sale_order_views.xml",
        "views/res_config_settings_views.xml",
        "views/res_users_views.xml",
    ],
    "installable": True,
    "application": False,
}
