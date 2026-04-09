{
    "name": "Sale Job Request",
    "summary": "Job Request สร้างจาก Sale Order และเชื่อมโยงกับ Delivery Order",
    "version": "18.0.1.0.0",
    "category": "Sales",
    "author": "Goldmints",
    "depends": ["sale", "sale_stock", "stock", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "data/job_request_sequence.xml",
        "data/job_request_server_actions.xml",
        "views/job_request_views.xml",
        "views/sale_order_views.xml",
        "views/stock_picking_views.xml",
    ],
    "application": False,
    "assets": {
        "web.assets_backend": [
            "sale_job_request/static/src/scss/job_request.scss",
        ],
    },
}
