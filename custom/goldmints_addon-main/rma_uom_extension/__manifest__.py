{
    "name": "RMA UoM FIFO Cost Extension",
    "version": "18.0.2.0.0",
    "summary": "Allow changing UoM on RMA lines, Lot breakdown, and FIFO cost calculation",
    "category": "Customization",
    "author": "Wolapart",
    "license": "OPL-1",
    "depends": ["rma_ept", "uom", "stock_account"],
    "data": [
        "security/ir.model.access.csv",
        "views/crm_claim_line_view.xml",
    ],
    "installable": True,
    "application": False
}
