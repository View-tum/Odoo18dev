{
    'name': 'Sale Order Customer Filter',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Hide Invoice/Delivery addresses from Customer dropdown',
    'description': 'Limits customer selection to company contacts by hiding invoice and delivery address entries.',
    'author': 'Wolapart',
    'depends': ['sale', 'sale_salesperson_customer_filter'],
    'data': [
        'views/sale_order_view.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
