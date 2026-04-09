{
    "name": "Sale Pro-Forma Report Style",
    "version": "18.0.1.0.0",
    "category": "Sales",
    "summary": "Beautify Pro-Forma Invoice layout (QWeb inherit)",
    "author": "365 Piyawat K.k",
    "depends": ["sale", "mail", "web"],   # เพิ่ม mail เพราะเรา inherit wizard mail
    "data": [
        "views/mail_compose_wizard_views.xml",
        "data/jasper_report.xml",
    ],
    "assets": {
        "web.report_assets_common": [
            "sale_report_saleorder_pro_forma/static/src/scss/report.scss",
        ],
    },
    "installable": True,
    "application": False,
}
