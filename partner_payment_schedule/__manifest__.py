# -*- coding: utf-8 -*-
{
    "name": "Partner Payment Schedule",
    "version": "18.0.1.1.0",
    "summary": "Customer payment schedules on partners with next-run computation.",
    "description": """Add an intuitive UI on contacts to define payment collection schedules by day-of-month or day-of-week, store the time of day, and compute the next execution.""",
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
    "installable": True,
    "application": False,
}
