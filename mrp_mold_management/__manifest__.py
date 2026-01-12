# -*- coding: utf-8 -*-
{
    "name": "MRP Mold Management",
    "version": "1.0",
    "category": "Manufacturing",
    "summary": "Mold tracking, cost calculation, and planning visibility.",
    "depends": ["mrp", "account", "mrp_account_enterprise"],
    "data": [
        "security/ir.model.access.csv",
        "views/mrp_mold_workcenter_views.xml",
        "views/mrp_mold_operation_views.xml",
        "views/mrp_mold_workorder_views.xml",
        "views/mrp_mold_mo_views.xml",
        "views/mrp_mold_planning_views.xml",
        "views/mrp_mold_report_views.xml",
    ],
    "installable": True,
    "application": False,
}
