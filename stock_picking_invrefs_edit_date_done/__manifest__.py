{
    "name": "stock_picking_invrefs_edit_date_done",
    "version": "18.0.1.0.0",
    "author": "Wolapart",
    "website": "https://365infotech.co.th",
    "license": "OPL-1",
    "summary": "Add Invs References on pickings and make Effective Date editable",
    "depends": ["stock"],
    "data": [
        "security/ir.model.access.csv",
        "views/stock_picking_views.xml",
        "data/picking_type_invoice_info.xml",
        "data/cron.xml"
    ],
    "installable": True
}
