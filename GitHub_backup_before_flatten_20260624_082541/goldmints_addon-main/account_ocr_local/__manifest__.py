{
    "name": "Local OCR Integration",
    "version": "18.0.1.0.0",
    "category": "Accounting",
    "summary": "Local self-hosted open-source OCR integration with Odoo Documents",
    "author": "Wolapart",
    "license": "OPL-1",
    "depends": ["base", "account", "account_invoice_extract", "documents_account"],
    "data": [
        "views/account_move_views.xml",
        "views/res_config_settings_views.xml"
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
