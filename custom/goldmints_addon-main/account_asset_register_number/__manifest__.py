{
    "name": "Account Asset Register Number",
    "version": "18.0.1.0.0",
    "category": "Accounting",
    "summary": "Auto-generate Fixed Asset Register Number (เลขทะเบียนคุม FIX ASSET)",
    "description": """
        This module adds a 'Register Number' field to the Fixed Asset form.
        It automatically generates a sequence number for each new asset.
        Compatible with Odoo Enterprise account_asset.
    """,
    "author": "Wolapart",
    "depends": ["account_asset"],
    "data": [
        "data/ir_sequence_data.xml",
        "views/account_asset_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "OPL-1",
}
