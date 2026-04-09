# purchase_order_status_report/__manifest__.py
{
    "name": "Purchase Order Status Report",
    "version": "18.0.1.0.0",
    "category": "Purchases",
    "summary": "Status report for Purchase Orders (PDF / XLSX)",
    "author": "Piyawat K.k",
    "website": "",
    "license": "AGPL-3",
    "depends": [
        "base",
        "purchase",      # ใช้ purchase.order
        "report_xlsx",   # ใช้ abstract model ของ report_xlsx
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizard/purchase_order_status_wizard_view.xml",
        "report/report_purchase_order_status_templates.xml",
        "report/paper_format.xml",
        "views/purchase_order_status_report_action.xml",
        "views/purchase_order_status_menus.xml",
    ],
    "assets": {
        "web.report_assets_common": [
            "purchase_order_status_report/static/src/scss/po_status_report.scss",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
