{
    "name": "Manufacturing Machine Report",
    "summary": "Wizard for Manufacturing Machine Report",
    "author": "(365) Piyawat K.k",
    "version": "1.0.0",
    "category": "Manufacturing",
    "depends": ["mrp", "stock", "product", "oi_jasper_report"],
    "data": [
        'security/ir.model.access.csv',
        "views/mrp_machine_report_wizard_view.xml",
        "views/mrp_machine_report_menu.xml"
    ],
    "installable": True,
    "application": False,
}