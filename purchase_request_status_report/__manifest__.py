# purchase_request_status_report/__manifest__.py
{
    "name": "Purchase Request Status Report",
    "version": "18.0.1.0.0",
    "category": "Purchases",
    "summary": "Status report for Purchase Requests (PDF / XLSX)",
    "author": "Piawat K.k",
    "website": "",
    "license": "AGPL-3",
    "depends": [
        "base",
        "purchase_request",   # โมดูล PR ที่คุณใช้อยู่
        "report_xlsx",        # ถ้าใช้ report_xlsx ของ OCA เหมือน WHT
        "purchase_request_menu_report",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizard/purchase_request_status_wizard_view.xml",
        "report/report_purchase_request_status_templates.xml",
        "report/paper_format.xml",
        "views/purchase_request_status_report_action.xml",
        "views/purchase_request_menus.xml",
    ],
    "assets": {
        "web.report_assets_common": [
            "purchase_request_status_report/static/src/scss/pr_status_report.scss",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
