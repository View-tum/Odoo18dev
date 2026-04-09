{
    "name": "MRP Scrap Auto Replenish",
    "version": "18.0.1.0.0",
    "summary": "Auto-replenish components from Shopfloor when marked as scrap.",
    "description": """
When a component is scrapped via mrp_parallel_console:
1. It checks if there is sufficient stock in the MO's source location.
2. If stock exists (matching lot or another lot), it will auto-add to the MO's raw moves.
3. If not, it creates an Internal Transfer from the main stock to replenish the components.
    """,
    "category": "Manufacturing",
    "author": "Wolapart",
    "license": "LGPL-3",
    "depends": [
        "mrp_parallel_console",
        "stock",
    ],
    "data": [],
    "installable": True,
    "application": False,
}