{
    'name' : 'Inventory and Stock Aging Report for Warehouse',
    'author': "Edge Technologies",
    'version' : '18.0.1.1',
    'live_test_url':'https://youtu.be/69n5iyMfHYg',
    "images":["static/description/main_screenshot.png"],
    'summary' : 'Product stock aging reports inventory aging report warehouse aging report product aging report for stock expiry report inventory expiry report stock overdue stock report due stock report product due report stock overdate report overdate stock reports.',
    'description' : """
        Stock inventory aging report filter by product, category, location, warehouse, date, and period length.
    """,
    'depends' : ['base','sale_management','stock'],
    "license" : "OPL-1",
    'data': [
            'security/ir.model.access.csv',
            'wizard/stock_aging_report_view.xml',
            'report/stock_aging_report.xml',
            'report/stock_aging_report_template.xml',
            ],
    'qweb' : [],
    'demo' : [],
    'installable' : True,
    'auto_install' : False,
    'price': 20,
    'currency': "EUR",
    'category' : 'Warehouse',
}
