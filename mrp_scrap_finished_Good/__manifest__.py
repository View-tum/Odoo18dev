{
    "name": "MRP Scrap Finished Good",
    "version": "18.0.1.0.0",
    "summary": "Limit scrap product selection to the MOs finished/by-products when opened from Shopfloor.",
    "license": "OPL-1",
    "author": "Wolapart",
    "website": "https://365infotech.co.th",
    "depends": ["mrp", "stock"],
    "data": [
        "security/ir.model.access.csv",
        "views/stock_scrap_views.xml"
    ],
    "installable": True
}
