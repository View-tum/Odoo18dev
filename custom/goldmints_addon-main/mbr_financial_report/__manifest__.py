{
    "name": "MBR Financial Report",
    "version": "18.0.1.0.0",
    "summary": "Management MBR report (Current Month / YTD vs Budget)",
    "description": "Management MBR report (Current Month / YTD vs Budget)",
    "author": "Phyo Thet Paing/paingphyothet561@gmail.com",
    "website": "https://www.365infotech.co.th/",
    "category": "Accounting/Reporting",
    "depends": [
                    "base", 
                    "account", 
                    "report_xlsx"
                ],
    "data": [
        "security/ir.model.access.csv",
        "views/mbr_account_map_views.xml",
        "report/mbr_report_views.xml",
        "report/mbr_report.xml",
        "wizard/mbr_report_wizard_views.xml",
       
    ],
    "post_init_hook": "_mbr_post_init",
    "license": "LGPL-3",
    "installable": True,
}
