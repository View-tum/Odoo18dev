{
    "name": "Vendor Billing Note",
    "version": "18.0.2.0.0",
    "category": "Purchases",
    "summary": "Create Vendor Billing Notes before generating Vendor Bills",
    "description": """
        This module adds a Billing Note step in the Purchase workflow.
        Process: PO -> Receive/Service Acceptance -> Billing Note -> Vendor Bill.
    """,
    "author": "365 Piyawat K.k",
    "depends": [
        "base",
        "purchase",
        "account",
        "purchase_order_status_report",
        "purchase_request_status_report",
        "purchase_service_acceptance",
        "discount_fixed_percent",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/sequence_data.xml",
        "wizard/create_bill_wizard_views.xml",
        "wizard/po_status_wizard_views_inherit.xml",
        "wizard/pr_status_wizard_views_inherit.xml",
        "report/pr_status_report_templates_inherit.xml",
        "views/vendor_billing_note_views.xml",
        "views/purchase_order_views.xml",
        "views/account_move_views.xml",
        "views/service_acceptance_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
