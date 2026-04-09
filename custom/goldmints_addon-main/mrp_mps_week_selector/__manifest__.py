{
    "name": "MPS Week Selector",
    "summary": "Select which weeks to replenish in MPS and group MOs by week name.",
    "version": "18.0.1.0.0",
    "category": "Manufacturing",
    "author": "Wolapart / 365 Infotech",
    "website": "https://www.365infotech.co.th/",
    "license": "LGPL-3",
    "depends": ["mrp_mps", "mrp"],
    "data": [
        "views/mrp_production_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "mrp_mps_week_selector/static/src/js/mps_week_selector.js",
            "mrp_mps_week_selector/static/src/xml/mps_week_selector.xml",
        ],
    },
    "installable": True,
    "application": False,
}
