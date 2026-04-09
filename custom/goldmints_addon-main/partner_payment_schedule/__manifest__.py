# -*- coding: utf-8 -*-
{
    "name": "Partner Payment Schedule",
    "version": "18.0.1.3.0",
    "summary": "Customer payment schedules with Calendar Multi-Select.",
    "description": """Add an intuitive UI on contacts to define payment collection schedules by day-of-month, day-of-week, or specific dates via a calendar picker.""",
    "category": "Customization",
    "author": "Wolapart",
    "website": "https://365infotech.co.th",
    "license": "OPL-1",
    "depends": ["base", "account"],
    "data": [
        "security/ir.model.access.csv",
        "data/pps_seed_data.xml",
        "views/partner_payment_schedule_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "partner_payment_schedule/static/src/components/**/*",
        ],
    },
    "installable": True,
    "application": False,
}
