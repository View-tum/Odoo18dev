{
    "name": "MRP Daily Reports (Jasper)",
    "summary": "Consolidated wizard for Production, Issue, and Scrap reports",
    "author": "365 Piyawat K.k",
    "version": "1.0.0",
    "category": "Manufacturing",
    "depends": ["mrp", "stock", "product", "oi_jasper_report"],
    "data": [
        "security/ir.model.access.csv",
        "data/jasper_report.xml",
        "views/mrp_daily_report_wizard_view.xml",
        "views/mrp_daily_report_menu.xml"
    ],
    "installable": True,
    "application": False,
}