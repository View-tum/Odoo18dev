# -*- coding: utf-8 -*-
{
    "name": "MPS to MO Tracking",
    "summary": "Track Manufacturing Orders created from MPS and make them easy to filter.",
    "version": "18.0.1.0.0",
    "category": "Manufacturing",
    "author": "Wolapart",
    "website": "https://365infotect.com",
    "license": "LGPL-3",
    "depends": ["mrp", "mrp_mps"],
    "data": [
        "security/ir.model.access.csv",
        "data/mps_batch_sequence.xml",
        "views/mrp_production_views.xml",
    ],
    "installable": True,
    "application": False,
}
